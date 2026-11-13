"""The five approved UI states, connected to the separately tested backend.

Layout: a navy sidebar (saved data, scenarios, reset) and a wide main area, so
the tables, the plan and the network board fit one laptop window.
"""
import os
import logging
import streamlit as st
from availability import calculate_availability
from data_model import State, ValidationError
from operations import RestockSession
from storage import JsonStore, StorageError, DEFAULT_STATE_PATH, SAMPLE_PATH
from ui_model import labels, money, quantity, rows_for, table_from_rows
from scenarios import list_scenarios
from teaching import certify, cheapest_first
from theme import TOKENS, DISPLAY_FONT
import explorer

st.set_page_config(page_title='Transportation System', layout='wide', initial_sidebar_state='expanded')
st.html(f"""<style>
[data-testid="stMainBlockContainer"]{{padding-top:3.6rem;padding-bottom:2rem;max-width:1500px}}
.st-key-headline{{margin-bottom:.6rem}}
.st-key-headline p{{font-family:{DISPLAY_FONT};font-weight:600;font-size:1.65rem;line-height:1.2;margin:0;color:{TOKENS['ink']}}}
</style>""")


def md(text):
    """Escape dollar signs so Streamlit markdown never reads amounts as math."""
    return text.replace('$', '\\$')


def sample():
    return State.from_json(SAMPLE_PATH.read_text(encoding='utf-8'))


def change_screen(screen, message=None):
    st.session_state.screen = screen
    st.session_state.epoch = st.session_state.get('epoch', 0) + 1
    if message:
        st.session_state.notice = message
    st.rerun()


def storage_failure():
    logging.getLogger(__name__).exception('Persistent state operation failed')
    st.session_state.blocked = True
    st.error('The save could not be verified. Reload saved data before making further changes. '
             'A completed save may already be on disk; do not repeat the old confirmation.')


def config(columns):
    return {'Location': st.column_config.TextColumn('Location'),
            **{f'v{n}': st.column_config.TextColumn(name, width='small') for n, name in enumerate(labels(columns).values())}}


def show_table(title, table, row_catalog, column_catalog):
    st.markdown(f'**{title}**')
    st.dataframe(rows_for(table, row_catalog, column_catalog), hide_index=True,
                 column_config=config(column_catalog), width='stretch')


def board(plan):
    """Network board: final plan by default; Explore algorithm replays how it was found."""
    exploring = st.session_state.get('exploring') == st.session_state.epoch
    if st.button('Show final plan' if exploring else 'Explore algorithm', key='explore'):
        st.session_state.exploring = None if exploring else st.session_state.epoch
        st.rerun()
    payload, reason = explorer.build_payload(plan.source_state, autoplay=exploring)
    if reason:
        st.info(reason)
    else:
        st.iframe(explorer.render_html(payload), height='content',
                  alt='Network board: warehouses, stores and the routes the plan uses')


def why_optimal(plan):
    state = plan.source_state
    proofs = certify(state, plan)
    planned = [p for p in proofs if p.max_units]
    if not all(p.optimal for p in proofs):
        st.error('The independent optimality check failed for this plan. Do not confirm it; report this result.')
        return
    st.markdown('**Why this plan is optimal**')
    st.markdown(md(
        f'{"The planned item ships" if len(planned) == 1 else f"Each of the {len(planned)} planned items ships"} the most it can '
        '(the smaller of total stock and total demand), and no loop of route changes, shipping more on some '
        'routes and less on others, would lower the cost. This is checked independently of the planner.'))
    greedy_allocation, greedy_cost = cheapest_first(state)
    extra = greedy_cost - plan.total_cost_cents
    if extra <= 0:
        st.caption(md('Filling the cheapest route first would also cost '
                      f'${money(greedy_cost)} here. The Greedy trap scenario shows where it fails.'))
        return
    names_w, names_s, names_i = labels(state.warehouses), labels(state.stores), labels(state.items)
    found = next((c for c in certify(state, allocation=greedy_allocation) if c.cycle), None)
    text = (f'Filling the cheapest route first would cost ${money(greedy_cost)}, '
            f'${money(extra)} more for the same units.')
    if found:
        route = lambda step: f'{names_w[step.warehouse_id]} to {names_s[step.store_id]}'
        more = ' and '.join(route(step) for step in found.cycle if step.more)
        less = ' and '.join(route(step) for step in found.cycle if not step.more)
        swap = f'ship more on {more}' + (f' and less on {less}' if less else '')
        text += (f' For {names_i[found.item_id]} it misses a cheaper rearrangement: {swap}, '
                 f'saving ${money(-found.cycle_cost_cents)} per unit moved.')
    st.caption(md(text))


def show_plan(plan, *, applied=False):
    state = plan.source_state
    remaining = sum(sum(row.values()) for row in plan.remaining_demand.values())
    needed = plan.units_shipped + remaining
    partial = remaining > 0
    cost = f'${money(plan.total_cost_cents)}'
    if applied:
        st.header('Partial restock confirmation' if partial else 'Restock confirmation')
        st.success(f'{"Partial restock" if partial else "Restock"} applied. '
                   f'{plan.units_shipped} units allocated; {remaining} units outstanding.')
        st.caption('This updates the project records; it does not book a real delivery.')
    else:
        st.header('Partial restock preview' if partial else 'Restock preview')
        if not plan.units_shipped:
            st.info('Nothing available to ship.' if remaining else 'No items need restocking.')
    if plan.units_shipped:
        verb = 'were allocated' if applied else 'ship'
        line = (f'{plan.units_shipped} of {needed} needed units {verb} for {cost}. '
                f'{remaining} units stay in store demand.' if partial else
                f'{plan.units_shipped} units {verb} for {cost}. All store demand is met.')
        with st.container(key='headline'):
            st.markdown(line)
    return partial


def preview_body(plan, partial):
    state = plan.source_state
    if plan.units_shipped:
        left, right = st.columns([5, 6], gap='medium')
        with left:
            st.markdown('**Proposed shipments**')
            st.dataframe([{'Item': labels(state.items)[s.item_id],
                           'From': labels(state.warehouses)[s.warehouse_id],
                           'To': labels(state.stores)[s.store_id], 'Units': str(s.quantity),
                           '$/unit': money(s.unit_cost_cents), 'Subtotal ($)': money(s.quantity*s.unit_cost_cents)}
                          for s in plan.shipments], hide_index=True, width='stretch')
            why_optimal(plan)
        with right:
            board(plan)
    titles = (['Availability by item'] if partial else []) + \
        ['Warehouse stock after confirmation', 'Store demand after confirmation']
    tabs = st.tabs(titles)
    if partial:
        with tabs[0]:
            st.dataframe([{'Item': labels(state.items)[item], 'Available': str(a.supply),
                           'Needed': str(a.demand), 'Unfilled': str(a.shortage)}
                          for item, a in calculate_availability(state).items()], hide_index=True)
    with tabs[-2]:
        show_table('Projected warehouse stock', plan.projected_inventory, state.warehouses, state.items)
    with tabs[-1]:
        show_table('Projected store demand', plan.remaining_demand, state.stores, state.items)
        if partial:
            st.caption('Outstanding demand stays saved across sessions until fulfilled or explicitly edited.')


def sidebar(controller):
    blocked = st.session_state.blocked
    with st.sidebar:
        st.title('Transportation System')
        st.caption('Plan the cheapest restock from warehouses to stores.')
        st.subheader('Scenarios')
        scenarios = {s.slug: s for s in list_scenarios()}
        choice = st.selectbox('Ready-made data', list(scenarios), key='scenario_choice',
                              format_func=lambda slug: scenarios[slug].title)
        picked = scenarios[choice]
        st.caption(md(f'{picked.purpose} Expected: {picked.expected_units} units for '
                      f'${money(picked.expected_cost_cents)}.'))
        if st.session_state.get('pending_load') != choice:
            if st.button('Load scenario', key='load_scenario', disabled=blocked):
                st.session_state.pending_load = choice
                st.rerun()
        else:
            st.warning(f'This replaces all working stock, demand and rates with “{picked.title}”. '
                       'The scenario file itself is not changed.')
            if st.button('Replace working data', key='confirm_load', type='primary', disabled=blocked):
                st.session_state.pending_load = None
                try:
                    controller.load_scenario(picked.state)
                    change_screen('inventory', md(f'Loaded “{picked.title}”. {picked.purpose}'))
                except StorageError:
                    storage_failure()
                except ValidationError as error:
                    st.error(str(error))
            if st.button('Keep current data', key='cancel_load'):
                st.session_state.pending_load = None
                st.rerun()
        st.subheader('Saved data')
        st.caption('Reload discards unsaved table edits and any preview. Reset replaces working values with the original sample.')
        if st.button('Reload saved data', key='reload'):
            try:
                controller.reload()
                st.session_state.blocked = False
                change_screen('inventory', 'Saved data reloaded.')
            except StorageError:
                storage_failure()
        with st.form('reset', enter_to_submit=False, border=False):
            agreed = st.checkbox('Replace my working values with the sample', key=f'reset_agreed_{st.session_state.epoch}')
            if st.form_submit_button('Reset to sample', key='reset', disabled=blocked):
                if not agreed:
                    st.error('Check the reset confirmation first.')
                elif not st.session_state.blocked:
                    try:
                        original = sample()
                        same_ids = all(set(getattr(original, c)) == set(getattr(controller.state, c))
                                       for c in ('items', 'warehouses', 'stores'))
                        # After a scenario load the IDs differ; the same consent covers replacing them.
                        controller.reset(original) if same_ids else controller.load_scenario(original)
                        change_screen('inventory', 'Sample values restored.')
                    except StorageError:
                        storage_failure()
                    except ValidationError as error:
                        st.error(str(error))


def inventory_screen(controller):
    state = controller.state
    outstanding = sum(sum(row.values()) for row in state.demand.values())
    st.header('Stock and store demand')
    st.markdown(f'**{outstanding} units outstanding** across {len(state.stores)} stores, supplied from '
                f'{len(state.warehouses)} warehouses, for {len(state.items)} item types.')
    epoch = st.session_state.epoch
    with st.form(f'tables_{epoch}', enter_to_submit=False, border=False):
        drafts = {}
        # Width follows each table's column count, so wide networks share space fairly.
        ni, ns = len(state.items), len(state.stores)
        columns = st.columns([ni + 1.4, ni + 1.4, ns + 1.4], gap='medium')
        for column, (name, title, row_catalog, column_catalog, costs) in zip(columns, (
                ('inventory', 'Warehouse inventory', state.warehouses, state.items, False),
                ('demand', 'Store demand: units missing', state.stores, state.items, False),
                ('shipping_costs_cents', 'Shipping cost per unit ($)', state.warehouses, state.stores, True))):
            with column:
                st.markdown(f'**{title}**')
                drafts[name] = st.data_editor(rows_for(getattr(state, name), row_catalog, column_catalog, costs=costs),
                    key=f'{name}_{epoch}', disabled=['Location'], hide_index=True, num_rows='fixed',
                    column_config=config(column_catalog), width='stretch')
        st.caption('Finish each cell with Enter or Tab and check its value, then save. Quantities are whole numbers; '
                   'prices are dollars with up to two decimals. One rate applies to every item type and is saved exactly in cents.')
        balance, actions = st.columns([3, 2], gap='large')
        with balance:
            st.markdown('**Supply and demand by item**')
            st.dataframe([{'Item': labels(state.items)[item], 'In stock': str(a.supply), 'Needed': str(a.demand),
                           'Can ship': str(min(a.supply, a.demand)), 'Short': str(a.shortage)}
                          for item, a in calculate_availability(state).items()], hide_index=True, width='stretch')
        with actions:
            preview = st.form_submit_button('Preview restock', key='preview', type='primary',
                                            disabled=st.session_state.blocked, width='stretch')
            save = st.form_submit_button('Save all changes', key='save', disabled=st.session_state.blocked, width='stretch')
            discard = st.form_submit_button('Discard table edits', key='discard', width='stretch')
            with st.expander('Add, set or remove one quantity'):
                st.caption('Save or discard table edits before using this shortcut.')
                choices = [(table, key) for table, catalog in [('inventory', state.warehouses), ('demand', state.stores)] for key in catalog]
                location = st.selectbox('Location', choices, format_func=lambda value:
                    f'{"Warehouse stock" if value[0] == "inventory" else "Store demand"}: '
                    f'{getattr(state, "warehouses" if value[0] == "inventory" else "stores")[value[1]]} [{value[1]}]')
                item = st.selectbox('Item', list(state.items), format_func=lambda key: labels(state.items)[key])
                operation = st.selectbox('Operation', ['add', 'set', 'remove'])
                amount = st.text_input('Quantity', value='0')
                quick = st.form_submit_button('Save quantity', key='quick', disabled=st.session_state.blocked)
    if discard:
        change_screen('inventory', 'Table edits discarded.')
    if (save or preview or quick) and not st.session_state.blocked:
        try:
            tables = {name: table_from_rows(drafts[name], rows, cols, costs=costs)
                      for name, rows, cols, costs in (
                          ('inventory', state.warehouses, state.items, False),
                          ('demand', state.stores, state.items, False),
                          ('shipping_costs_cents', state.warehouses, state.stores, True))}
            dirty = any(tables[name] != getattr(state, name) for name in tables)
            if save:
                controller.edit_tables(expected_state=state, **tables)
                change_screen('inventory', 'All changes saved.' if dirty else 'No changes to save.')
            elif dirty:
                st.error('Save or discard table changes before previewing or using the quantity shortcut.')
            elif quick:
                controller.edit_quantity(*location, item, quantity(amount), operation)
                change_screen('inventory', 'Quantity saved.')
            else:
                controller.preview()
                change_screen('preview')
        except ValidationError as error:
            st.error(str(error))
        except StorageError:
            storage_failure()


def preview_screen(controller):
    preview = controller.pending_preview
    head, actions = st.columns([3, 1], vertical_alignment='top')
    with head:
        partial = show_plan(preview.plan)
    with actions:
        confirm = st.button('Approve partial restock' if partial else 'Confirm restock', key='confirm', type='primary',
                            disabled=not preview.can_confirm or st.session_state.blocked, width='stretch')
        cancel = st.button('Cancel', key='cancel', width='stretch')
    st.caption('Confirming deducts only the shipped units from stock and store demand. Cancel changes nothing.')
    if confirm and not st.session_state.blocked:
        try:
            controller.confirm(preview)
            st.session_state.last_plan = preview.plan
            change_screen('confirmation')
        except StorageError:
            storage_failure()
        except ValidationError as error:
            st.error(str(error))
    if cancel:
        controller.cancel(preview)
        change_screen('inventory')
    preview_body(preview.plan, partial)


def confirmation_screen():
    plan = st.session_state.last_plan
    state = plan.source_state
    show_plan(plan, applied=True)
    if st.button('Back to inventory', key='back'):
        change_screen('inventory')
    left, right = st.columns(2, gap='large')
    with left:
        show_table('Updated warehouse inventory', plan.projected_inventory, state.warehouses, state.items)
    with right:
        show_table('Remaining store demand, saved', plan.remaining_demand, state.stores, state.items)
    if sum(sum(row.values()) for row in plan.remaining_demand.values()):
        st.caption('Outstanding demand stays saved across sessions until fulfilled or explicitly edited.')


try:
    store = JsonStore(os.environ.get('TRANSPORTATION_STATE_PATH', str(DEFAULT_STATE_PATH)))
    if 'controller' not in st.session_state:
        if not store.path.exists():
            st.title('Transportation System')
            st.info('Create a working copy of the sample to begin. The original sample stays unchanged.')
            if st.button('Create sample workspace', key='initialize'):
                store.initialize(sample())
                st.rerun()
            st.stop()
        st.session_state.controller = RestockSession.open(store)
        st.session_state.screen = 'inventory'
        st.session_state.epoch = 0
        st.session_state.blocked = False
except StorageError:
    st.title('Transportation System')
    st.error('Saved data could not be opened. The file has not been reset or overwritten. '
             'Check the configured JSON file and its folder, then retry.')
    if st.button('Retry loading', key='retry'):
        st.rerun()
    st.stop()

controller = st.session_state.controller
sidebar(controller)
if 'notice' in st.session_state:
    st.success(st.session_state.pop('notice'))
if st.session_state.blocked:
    st.warning('Changes are paused until saved data is successfully reloaded.')

if st.session_state.screen == 'inventory':
    inventory_screen(controller)
elif st.session_state.screen == 'preview':
    preview_screen(controller)
else:
    confirmation_screen()
