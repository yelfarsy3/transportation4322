"""The five approved UI states, connected to the separately tested backend."""
import os
import logging
import streamlit as st
from availability import calculate_availability
from data_model import State, ValidationError
from operations import RestockSession
from storage import JsonStore, StorageError, DEFAULT_STATE_PATH, SAMPLE_PATH
from ui_model import labels, money, quantity, rows_for, table_from_rows

st.set_page_config(page_title='Transportation System', layout='centered')
st.title('Transportation System')


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
            **{f'v{n}': st.column_config.TextColumn(name) for n, name in enumerate(labels(columns).values())}}


def show_table(title, table, row_catalog, column_catalog):
    st.subheader(title)
    st.dataframe(rows_for(table, row_catalog, column_catalog), hide_index=True,
                 column_config=config(column_catalog), width='stretch')


def show_plan(plan, *, applied=False):
    state = plan.source_state
    remaining = sum(sum(row.values()) for row in plan.remaining_demand.values())
    partial = remaining > 0
    if applied:
        st.header('Partial restock confirmation' if partial else 'Restock confirmation')
        st.success(f'{"Partial restock" if partial else "Restock"} applied. '
                   f'{plan.units_shipped} units allocated; {remaining} units outstanding.')
        st.caption('This updates the project records; it does not book a real delivery.')
    else:
        st.header('Partial restock preview' if partial else 'Restock preview')
        if not plan.units_shipped:
            st.info('Nothing available to ship.' if remaining else 'No items need restocking.')
        elif partial:
            st.warning(f'{plan.units_shipped} of {plan.units_shipped + remaining} needed units can ship. '
                       f'{remaining} units will remain in store demand.')
        else:
            st.info('All store demand can be met. Review the shipments below.')
    st.write(f'**{plan.units_shipped} units · Shipping cost: ${money(plan.total_cost_cents)}**')
    if partial and not applied:
        st.subheader('Availability by item')
        st.dataframe([{'Item': labels(state.items)[item], 'Available': str(a.supply),
                       'Needed': str(a.demand), 'Unfilled': str(a.shortage)}
                      for item, a in calculate_availability(state).items()], hide_index=True)
    if not applied:
        st.subheader('Proposed shipments')
        st.dataframe([{'Item': labels(state.items)[s.item_id],
                       'From': labels(state.warehouses)[s.warehouse_id],
                       'To': labels(state.stores)[s.store_id], 'Units': str(s.quantity),
                       '$/unit': money(s.unit_cost_cents), 'Subtotal ($)': money(s.quantity*s.unit_cost_cents)}
                      for s in plan.shipments], hide_index=True, width='stretch')
    show_table('Updated warehouse inventory' if applied else 'Warehouse stock after confirmation',
               plan.projected_inventory, state.warehouses, state.items)
    show_table('Remaining store demand — saved' if applied else 'Store demand after confirmation',
               plan.remaining_demand, state.stores, state.items)
    if remaining:
        st.caption('Outstanding demand stays saved across sessions until fulfilled or explicitly edited.')
    return partial


try:
    store = JsonStore(os.environ.get('TRANSPORTATION_STATE_PATH', str(DEFAULT_STATE_PATH)))
    if 'controller' not in st.session_state:
        if not store.path.exists():
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
    st.error('Saved data could not be opened. The file has not been reset or overwritten. '
             'Check the configured JSON file and its folder, then retry.')
    if st.button('Retry loading', key='retry'):
        st.rerun()
    st.stop()

controller = st.session_state.controller
if 'notice' in st.session_state:
    st.success(st.session_state.pop('notice'))
if st.session_state.blocked:
    st.warning('Changes are paused until saved data is successfully reloaded.')
with st.expander('Saved data and reset'):
    st.caption('Reload discards unsaved table edits and any preview. Reset replaces working values with the original sample.')
    if st.button('Reload saved data', key='reload'):
        try:
            controller.reload()
            st.session_state.blocked = False
            change_screen('inventory', 'Saved data reloaded.')
        except StorageError:
            storage_failure()
    with st.form('reset', enter_to_submit=False):
        agreed = st.checkbox('Replace my working values with the sample', key=f'reset_agreed_{st.session_state.epoch}')
        if st.form_submit_button('Reset to sample', key='reset', disabled=st.session_state.blocked):
            if not agreed:
                st.error('Check the reset confirmation first.')
            elif not st.session_state.blocked:
                try:
                    controller.reset(sample())
                    change_screen('inventory', 'Sample values restored.')
                except StorageError:
                    storage_failure()
                except ValidationError as error:
                    st.error(str(error))

if st.session_state.screen == 'inventory':
    state = controller.state
    st.header('Stock and store demand')
    st.caption(f'{len(state.warehouses)} warehouses · {len(state.stores)} stores · {len(state.items)} item types')
    outstanding = sum(sum(row.values()) for row in state.demand.values())
    st.write(f'**{outstanding} units outstanding**')
    st.caption('Edit one or several cells. Finish each cell with Enter or Tab and check its displayed value, then Save all changes. '
               'Use whole numbers for quantities and dollars with up to two decimal places for prices.')
    epoch = st.session_state.epoch
    with st.form(f'tables_{epoch}', enter_to_submit=False):
        drafts = {}
        for name, title, row_catalog, column_catalog, costs in (
                ('inventory', 'Warehouse inventory', state.warehouses, state.items, False),
                ('demand', 'Store demand — units missing', state.stores, state.items, False),
                ('shipping_costs_cents', 'Shipping cost per unit ($)', state.warehouses, state.stores, True)):
            st.subheader(title)
            drafts[name] = st.data_editor(rows_for(getattr(state, name), row_catalog, column_catalog, costs=costs),
                key=f'{name}_{epoch}', disabled=['Location'], hide_index=True, num_rows='fixed',
                column_config=config(column_catalog), width='stretch')
        st.caption('The same shipping rate applies to every item type. Prices are saved exactly in cents.')
        save = st.form_submit_button('Save all changes', key='save', disabled=st.session_state.blocked)
        discard = st.form_submit_button('Discard table edits', key='discard')
        preview = st.form_submit_button('Preview restock', key='preview', type='primary', disabled=st.session_state.blocked)
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
elif st.session_state.screen == 'preview':
    preview = controller.pending_preview
    partial = show_plan(preview.plan)
    st.caption('Confirm to deduct only shipped units from stock and store demand. Cancel changes nothing.')
    if st.button('Approve partial restock' if partial else 'Confirm restock', key='confirm',
                 type='primary', disabled=not preview.can_confirm or st.session_state.blocked) and not st.session_state.blocked:
        try:
            controller.confirm(preview)
            st.session_state.last_plan = preview.plan
            change_screen('confirmation')
        except StorageError:
            storage_failure()
        except ValidationError as error:
            st.error(str(error))
    if st.button('Cancel', key='cancel'):
        controller.cancel(preview)
        change_screen('inventory')
else:
    show_plan(st.session_state.last_plan, applied=True)
    if st.button('Back to inventory', key='back'):
        change_screen('inventory')
