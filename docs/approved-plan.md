# MTH 4322 — Transportation System

Final implementation plan · Python + Streamlit

We're ready to begin building. The UI rough draft is approved, the restocking objective is established, and we have enough information to define an implementation plan without introducing unnecessary complexity.

My recommendation is to build the project in **10 controlled stages**, where every stage produces something testable before we proceed.

The principle throughout will be\:

**Understand → Implement → Test → Challenge → Approve → Continue.**

We cannot guarantee that no bugs will occur. What we can do is structure the work so mistakes are caught early, isolated, and corrected before they affect later components.

## 1\. Final project specification

These will be our starting assumptions. We can revise them if testing reveals a problem, but we should not silently change them during implementation.

| Decision | Finalized approach |
|--------|--------|
| Language | Python |
| Interface | Streamlit |
| Main algorithm | Minimum-cost maximum-flow |
| Shortage handling | Ship the maximum possible quantity, then minimize cost |
| Fairness | Not an additional optimization constraint |
| Different item types | Optimized independently |
| Shipping costs | Same warehouse-to-store cost for every item type |
| Quantities | Nonnegative integers |
| Costs | Nonnegative amounts, stored as integer cents |
| Restock | Preview first, then confirm |
| Unfulfilled demand | Remains saved |
| Persistence | Local JSON |
| Multiple users | Outside initial scope |
| External optimization libraries | Not allowed |
| Initial UI | Your approved five-screen draft |

These are consistent with the transportation assignment's stated requirements and with our chosen behavior for the decisions Professor Sheffer leaves open. fileciteturn0file1L4-L28

### Exact algorithm contract

For every item type \(i\), let \(S_i\) be total available stock and \(D_i\) total demand.

Because the assignment provides a shipping cost for every warehouse–store pair, and we aren't imposing shared transportation limits, the maximum number of units that can be shipped is\:

\[
F_i=\min(S_i,D_i)
\]

Our algorithm must ship exactly \(F_i\) units while minimizing their total transportation cost.

The result must contain the shipment quantities, the total shipping cost, the projected warehouse inventory, and the remaining store demand.

If all demand is fulfilled, that's a complete restock. Otherwise, it's a partial restock. **The optimizer is the same in both cases.**

## 2\. Project architecture

I recommend a small, modular project, not a large application architecture.

How the application will work

**Streamlit UI**

Displays tables, accepts edits, previews plans

**Application logic**

Validates edits, prepares restocks, confirms changes

**Optimization algorithm**

Calculates the cheapest maximum shipment plan

**JSON data storage**

Inventory, demand, prices, and saved state

Conceptual architecture. The optimizer receives data and returns a plan; it must never change the stored inventory itself.

The separation is essential. If a calculation is wrong, we should be able to test the algorithm without starting Streamlit. If a button doesn't work, we should be able to debug the UI without questioning the algorithm.

### Proposed project structure

```text
transportation-system/
├── app.py
├── data_model.py
├── optimizer.py
├── operations.py
├── storage.py
├── requirements.txt
├── README.md
│
├── data/
│   ├── sample.json
│   └── current_state.json
│
├── tests/
│   ├── test_data_model.py
│   ├── test_optimizer.py
│   ├── test_operations.py
│   ├── test_storage.py
│   └── brute_force_reference.py
│
└── docs/
    ├── initial-ui-design.pdf
    └── verification-log.md
```

These files are responsibilities, not a mandate to build them all at once. We'll create them when their stage begins.

We will use ordinary Python structures and standard libraries such as `heapq`, `json`, and `unittest`\. Streamlit will be the main external dependency.

## 3\. Step-by-step implementation roadmap

1. **Stage 1 — Set up the environment and project**
   
   Create the project folder, check the installed Python version, establish a virtual environment, install Streamlit, initialize Git, and create a minimal runnable application.
   
   We will also preserve your UI design separately from working files.
   
   **Tests\:** Confirm Python and Streamlit start, the expected environment is being used, and the application loads without exceptions.
   
   Exit requirement: We can launch and close the basic application reliably.
2. **Stage 2 — Implement the data model**
   
   Define how item types, warehouses, stores, inventory, demand, and shipping prices are represented. Assign stable IDs so renaming a location doesn't break references.
   
   Define validation rules and create the original two-warehouse, two-store sample dataset from your UI draft.
   
   **Tests\:** Read and update quantities, calculate totals, reject invalid values, and verify that item types are never confused.
   
   Exit requirement: The data is consistent, independently inspectable, and validated.
3. **Stage 3 — Implement stock and demand calculations**
   
   Build functions that calculate total supply, total demand, available shipment quantities, and shortages separately for each item.
   
   No optimization algorithm yet.
   
   **Tests\:** Compare computed totals against manually calculated examples, including exact supply, excess stock, shortages, and zero demand.
   
   Exit requirement: We know exactly how many units can be shipped before calculating where they should go.
4. **Stage 4 — Build an independent testing reference**
   
   Create a brute-force checker for tiny instances. It will enumerate feasible shipment allocations and identify the cheapest one.
   
   This is strictly a testing tool, not the production optimization algorithm.
   
   **Tests\:** Check its answers manually on several small examples. Use fixed random seeds for reproducible cases.
   
   Exit requirement: We have a trustworthy way to independently check small optimization results.
5. **Stage 5 — Build the minimum-cost-flow algorithm**
   
   Implement the graph with source, warehouse, store, and sink vertices.
   
   Add capacities, shipping costs, residual edges, and augmenting paths. Initially use a straightforward shortest-path method that correctly handles negative residual edge costs.
   
   **Tests\:** Verify the \$4 greedy counterexample, full-restock examples, partial-restock examples, tied costs, and cases requiring reassignment of earlier flow.
   
   Compare every small random result against the brute-force checker.
   
   Exit requirement: The algorithm returns valid, demonstrably optimal results on our independently verifiable cases.
6. **Stage 6 — Optimize and analyze running time**
   
   Improve shortest-path searches using Dijkstra with vertex potentials.
   
   We will explain why reduced costs are nonnegative before relying on Dijkstra. We won't simply replace one algorithm with another because it appears faster.
   
   **Tests\:** Compare the optimized solver with the original solver, rerun the entire small-case test suite, and benchmark larger inputs.
   
   Exit requirement: The optimized implementation preserves correctness and we can explain its asymptotic running time.
7. **Stage 7 — Implement restock preview and confirmation**
   
   Translate flow results into shipment instructions.
   
   Preview must not mutate data. Confirmation must verify that the data hasn't changed since preview, then deduct shipped quantities from warehouse stock and store demand.
   
   **Tests\:** Preview, cancel, confirm, repeated confirmation, changed shipping prices, changed inventory, full and partial restocks.
   
   Exit requirement: Every confirmed plan updates inventory and demand exactly once, with no partial updates on failure.
8. **Stage 8 — Implement JSON persistence**
   
   Save inventory, demand, shipping costs, and a state version. Preserve the original sample dataset separately.
   
   Use a temporary file and replacement to reduce the risk of leaving a partially written JSON file.
   
   **Tests\:** Save, reopen, reload, reset to sample, reject malformed data, and verify outstanding demand survives a restart.
   
   Exit requirement: Data survives application restarts and does not silently reset or become inconsistent.
9. **Stage 9 — Build and connect the Streamlit interface**
   
   Implement the approved five states: main page, full preview, full confirmation, partial preview, and partial confirmation.
   
   Use one common preview component and one confirmation component with conditionally displayed information.
   
   **Tests\:** Check every action, displayed quantity, edited value, transition, error message, and reload behavior.
   
   Exit requirement: The complete user workflow matches the approved draft and the tested backend.
10. **Stage 10 — Final validation and presentation preparation**
    
    Run the complete tests, randomized comparisons, performance checks, manual UI walkthroughs, and failure scenarios.
    
    Prepare the project repository, README, screenshots, AI chat record, and explanation of verification at each stage.
    
    **Tests\:** Start from a fresh setup and repeat a complete demonstration without relying on hidden application state.
    
    Exit requirement: The project is reproducible and we can explain, demonstrate, and defend its behavior.

Stages 1–4 deliberately come before the algorithm. That is not unnecessary preparation: the data contract and the independent testing reference are what will let us detect an incorrect optimizer.

## 4\. Define the data and function contracts now

Before Stage 2, we should know what information each major function receives and returns.

| Component | Responsibility | Must not do |
|--------|--------|--------|
| `data_model.py` | Define and validate the application state | Choose shipment routes |
| `optimizer.py` | Calculate minimum-cost maximum shipments | Modify inventory or write files |
| `operations.py` | Apply user edits and confirmed plans | Invent or alter optimizer results |
| `storage.py` | Load and save validated application state | Decide which shipments are optimal |
| `app.py` | Present information and handle user actions | Contain its own optimization algorithm |

The most important operations will have these contracts\:

**`compute_restock_plan(state)`**

Receives valid current state and returns shipment allocations, total cost, units shipped, and outstanding demand. It does not modify its input.

**`validate_plan(state, plan)`**

Checks stock limits, demand limits, shipping-cost totals, shipped flow, and that all requested quantities and locations are valid. This verifies feasibility and internal consistency; it does not independently prove the plan is globally optimal.

**`apply_restock(state, plan)`**

Rejects a plan generated from outdated state, validates its quantities, creates a completely updated state, and saves that state only when the operation can complete successfully.

This contract is what prevents previewing a shipment from accidentally executing it.

### State handling

We will distinguish three types of information\:

- **Persistent state\:** Actual inventory, current demand, shipping prices, and state version.
- **Computed preview\:** Proposed shipments and projected results based on a particular persistent-state version.
- **Display state\:** Which screen or message Streamlit is currently showing.

A preview becomes invalid when stock, demand, or shipping prices change. Confirmation must recheck the persistent state, rather than trusting whatever values were previously displayed.

For the initial version, we'll assume one user operating the app locally. Simultaneous multi-user editing would require additional concurrency protection.

## 5\. Our concrete testing baseline

We won't start by generating hundreds of random tests. First, we'll establish exact, independently calculated answers.

Baseline test cases

| **Test A**<br><br>Original UI data | 10 units shipped, total cost **\$14**\. All store demands become zero. |
|--------|--------|
| **Test B**<br><br>Partial-restock UI data | 12 units shipped, total cost **\$20**\. Two monitors remain outstanding at Store Y. |
| **Test C**<br><br>Greedy counterexample | Optimal cost **\$4**, not \$101. |
| **Test D**<br><br>All demand is zero | Zero shipments, \$0 cost, and no confirmation needed. |
| **Test E**<br><br>No stock available | Zero shipments, unchanged demand, and confirmation disabled. |

### Beyond those five cases

We'll introduce randomized testing in two separate ways.

For small instances, the brute-force reference must agree with the optimized solver on the minimum number of outstanding units and minimum total cost. Different shipment allocations are acceptable if they achieve the same optimum.

For larger instances, where exhaustive enumeration is impractical, we test invariants and useful mathematical properties. For example\:

- Shipments never exceed available stock.
- Fulfilled quantities never exceed demand.
- Total cost equals the sum of shipment subtotals.
- Maximum flow for each item equals the smaller of total stock and demand.
- Adding more available inventory cannot increase the minimum cost of satisfying a fixed full demand.
- Increasing every route's price by \$1 increases the optimal cost by exactly \$1 times the number of units shipped, provided the maximum shipment quantity remains unchanged.

We will record the number of tests run, any failures, corrections, and rerun results. **A passing test suite is evidence, not a substitute for understanding the algorithm.**

## 6\. Algorithm implementation details we'll need to understand

The finished optimizer will use the successive shortest augmenting path method.

For a single item type, we will construct\:

\[
V=n_2+n_3+2
\]

vertices and

\[
E=n_2n_3+n_2+n_3
\]

forward edges, with corresponding residual edges.

Each successful augmentation sends at least one whole unit. Since \(m\) is the total demand across all item types, there are at most \(m\) augmentations.

The optimized Dijkstra-with-potentials implementation will have a worst-case running-time bound of approximately\:

\[
O\left(
n_1(n_2+n_3)
+kE+
mE\log V
\right)
\]

where \(k\leq n_1\) is the number of item types with positive demand, plus the one-time cost of reading the shared \(n_2\times n_3\) shipping-price table.

For the proposed data representation, this gives a straightforward upper bound\:

\[
\boxed{
O\left(
n_1n_2n_3+
m n_2n_3\log(n_2+n_3)
\right)
}
\]

assuming positive numbers of warehouses and stores.

We should be able to explain this in terms of vertices, edges, shortest-path searches, and the maximum number of augmentations. We should also understand that this bound depends on \(m\), the numerical quantity of missing units, not merely on the number of stores and warehouses.

Professor Sheffer requires you to understand the algorithm and its running time, even though that explanation is not a required written submission. fileciteturn0file0L48-L54

## 7\. How we control mistakes during implementation

For every stage, we'll follow the same review process.

Required stage review

1. Explain what we're adding and why it is necessary.
2. Make the smallest practical implementation change.
3. Run targeted tests, including at least one failure or edge case.
4. Inspect the result independently of the new implementation where possible.
5. Explain any failures and correct the underlying cause.
6. Run regression tests to check that earlier behavior still works.
7. Record the checks and results before proceeding.

We'll use Git to create a meaningful checkpoint after each completed stage, but passing tests will not automatically mean a stage is approved. You should be able to explain the major decisions and understand any important correction.

The verification log will record actual commands, observed outputs, screenshots where useful, failures, and corrections. We won't claim checks were performed unless they were.

This also directly follows Professor Sheffer's project instructions to develop the system incrementally, test standard inputs, edge cases, and random inputs, and maintain evidence of verification. fileciteturn0file0L18-L45

## 8\. Things we will intentionally defer

These aren't reasons to delay implementation. They are boundaries that keep the first version manageable.

| Topic | Decision |
|--------|--------|
| Store fairness during shortages | Not included; minimum cost takes priority after maximum fulfillment |
| Shared vehicle capacity | Not included |
| Different costs by item type | Not included |
| Warehouse-to-warehouse transfers | Not included |
| User authentication | Not included |
| Networked store/warehouse clients | Optional advanced extension, not initial scope |
| Live database | Not needed for local demonstration |
| Shipping transactions with real carriers | Not included |
| Historical shipment analytics | Optional after core functionality works |
| UI styling refinements | After the full workflow functions |

We will still fix genuine defects or inconsistencies whenever we encounter them. We just won't allow unrelated enhancements to displace the core algorithm.

## 9\. Final completion criteria

At the end, the project should satisfy all of the following\:

**Project acceptance checklist** /

Track completion only after a requirement has been verified. All items begin unchecked.

## 10\. Where we start

**The next action is Stage 1: environment setup, followed immediately by Stage 2: the data model.**

We'll begin by checking Python and the existing development environment, establishing the project structure, and loading the exact sample data from your approved UI draft.

The first meaningful implementation milestone will be a Python program that can represent and validate the two warehouses, two stores, item quantities, and shipping costs without any optimization logic.

Once that passes its tests, we'll implement availability calculations, then the brute-force reference, and finally the actual optimizer.

One course-policy detail to preserve: your AI prompts must remain your own, and the initial design should be documented accurately according to how it was created. The project instructions specifically require the AI conversation log and your personally verified checks, so we'll maintain those throughout rather than assembling them retrospectively.

**I approve this plan as our implementation roadmap.** It gives us a clear first task, explicit boundaries for each component, and a verification gate before every major dependency. We can start building from Stage 1 without another planning round.
