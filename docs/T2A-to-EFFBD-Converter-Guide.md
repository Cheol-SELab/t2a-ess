<!-- Copyright: SELab.AI (c) 2026 -->

# T2A-ESS → EFFBD SysML Converter Developer Guide

This converter turns the **T2A-ESS slot JSON** produced by text2activity into **SysML for the EFFBD diagrams of
selab-effbd-editor**. This document summarizes the purpose, how to run it,
a **small real example (input→output)**, the mapping rules, the structure, and the limitations so that other developers can quickly understand and use it.

- Code: `src/t2a_sysml/`
- CLI: `src/convert_t2a_to_sysml.py`
- Example: `src/examples/coffee_order_T2A-ESS.json` → `coffee_order.sysml`

## 1. Position in the overall pipeline

```text
Natural-language scenario
  └─(text2activity)→ T2A-ESS slot JSON  (scenarios·episodes·performers·actions·
                                          items·flows·controls·slot_relations …)
        └─(this converter)→ EFFBD SysML (.sysml)
              └─ load into selab-effbd-editor → EFFBD diagram
```

This converter is the stage **after the slot JSON**. Extraction of the slots themselves is handled by text2activity.

## 2. Quick start

```powershell
# Default (canonical EFFBD editor form) + structure validation
python src/convert_t2a_to_sysml.py <T2A-ESS.json> -o out.sysml --validate

# Run the example
python src/convert_t2a_to_sysml.py `
  src/examples/coffee_order_T2A-ESS.json -o src/examples/coffee_order.sysml --validate
```

Options:
- `--no-imm-tags` : plain form (`business_example`) without IMM tags (`#Performer`/`#Function`).
- `--validate` : reports `schema:` checks (Slot Relation contract — relation type/endpoint, custom relations, state-axis completeness) + `effbd:` checks (reference resolution + start→done reachability + item-flow completeness). Exits with 4 if there is at least one error.
- `--validate-only` : runs the same checks as `--validate` but does not write the .sysml.
- `--state` : also outputs the **State View** (standard SysML v2 `state def`) of the state axis (default `<output>.state.sysml`).
- `--state-output PATH` : sets the state view output path explicitly (implies `--state`).

## 3. Worked example — "Cafe Order"

A small scenario that shows the core features (nested episodes · fork/join concurrency · guarded decision · item flow) at a glance.

### 3.1 Input (T2A-ESS slot JSON summary)

Only the essentials of `src/examples/coffee_order_T2A-ESS.json`:

| Slot | Value |
|---|---|
| performers | Customer, Clerk, Barista |
| episodes | `Order Intake`(1) → `Drink Preparation`(2) |
| actions | Place Order, Payment · Make Drink, Preheat Cup, Serve |
| items | Order Slip |
| flows | Order→Payment(control), Make→Serve(control), Preheat→Serve(control), **Order Slip(object)** |
| controls | `Payment Completion Check`(decision, guard=`Payment Complete`) → governs the Order→Payment flow |

Relation (`slot_relations`) excerpt:

```text
SCN --has_episode--> EP_ORDER, EP_MAKE
EP_ORDER --contains_action--> Place Order, Payment  # the episode owns the actions
A_PLACE_ORDER --performed_by--> Customer           # performer
A_PLACE_ORDER --produces_item--> Order Slip      # out item
A_MAKE_DRINK  --uses_item-->     Order Slip      # in item
F_ORDER_TO_PAY --flow_source--> Place Order, --flow_target--> Payment   # ordering
C_PAID_GUARD  --controls_flow--> F_ORDER_TO_PAY # guard on this flow
```

### 3.2 Output (EFFBD SysML)

```sysml
private import IMMBaseSchema::*;
private import ScalarValues::*;

item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;

#Performer
part 'Customer' : Performer;
#Performer
part 'Clerk' : Performer;
#Performer
part 'Barista' : Performer;

#Function
action 'Coffee Order Scenario' {
    #Function
    action 'Order Intake' {                          // ← episode 1 (nested function)
        #Function
        action 'Place Order' {
            out item 'Order Slip' : ItemOutputEdge; // ← produces_item
        }
        #Function
        action 'Payment';

        attribute 'Payment Complete' : ScalarValues::Boolean;  // control: decision  ← guard

        allocate 'Place Order' to 'Customer';             // ← performed_by
        allocate 'Payment' to 'Clerk';

        succession first start then 'Place Order';
        succession first 'Place Order' if 'Payment Complete' == true then 'Payment';  // ← guarded succession
        succession first 'Payment' then done;
    }
    #Function
    action 'Drink Preparation' {                          // ← episode 2
        #Function
        action 'Make Drink' {
            in item 'Order Slip' : ItemInputEdge;    // ← uses_item
        }
        #Function
        action 'Preheat Cup';
        #Function
        action 'Serve';

        fork 'New Start Concurrency_1';           // ← parallelism inference (Make ∥ Preheat)
        join 'New End Concurrency_1';

        allocate 'Make Drink' to 'Barista';
        allocate 'Preheat Cup' to 'Barista';
        allocate 'Serve' to 'Barista';

        succession first start then 'New Start Concurrency_1';
        succession first 'New Start Concurrency_1' then 'Make Drink';
        succession first 'New Start Concurrency_1' then 'Preheat Cup';
        succession first 'Make Drink' then 'New End Concurrency_1';
        succession first 'Preheat Cup' then 'New End Concurrency_1';
        succession first 'New End Concurrency_1' then 'Serve';
        succession first 'Serve' then done;
    }

    item 'Order Slip';

    succession first start then 'Order Intake';        // ← episode sequencing
    succession first 'Order Intake' then 'Drink Preparation';
    succession first 'Drink Preparation' then done;

    // cross-episode object flow (3-level dotted path)
    flow from 'Order Intake'.'Place Order'.'Order Slip' to 'Drink Preparation'.'Make Drink'.'Order Slip';
}
```

`--validate-only` result: `validate: schema errors=0 warnings=0 | effbd ok=True errors=0 warnings=0`.

### 3.3 Editor rendering result

When the `.sysml` above is loaded into selab-effbd-editor, it is rendered like this:

![EFFBD diagram rendering of the cafe order example](img/generated-effbd.jpg)

Rendered elements ↔ SysML/slot correspondence:

| Diagram | SysML | T2A-ESS slot |
|---|---|---|
| Left/right filled circles | `start` / `done` | (automatic framing) |
| `Lv.0 Coffee Order Scenario` outer frame | root `action 'Coffee Order Scenario'` | `scenarios[0]` |
| `Lv.1 Order Intake` · `Lv.1 Drink Preparation` blocks | nested `action '<episode>'` | `episodes[]` |
| `Lv.2` boxes (performer label at the bottom) | `#Function action '<label>'` + `allocate … to …` | `actions[]` + `performed_by` |
| `Payment Complete` (label on the edge) | `succession … if 'Payment Complete' == true …` | `controls`(decision) `guard_texts` |
| **AND** node | `fork` / `join` | unguarded multiple branches (graph inference) |
| `Order Slip` box + diagonal line | `flow from 'Order Intake'.'Place Order'.'Order Slip' to 'Drink Preparation'.'Make Drink'.'Order Slip'` | object `flow` + `carries_item` |
| `Barista` label on the edge | `allocate … to 'Barista'` of the branching actions | `performed_by` |

In other words, slot → SysML → **diagram** is traced 1:1: episodes appear as nested blocks (Lv.1), actions as
`#Function` boxes (Lv.2), parallelism as **AND** gates (fork/join), decisions as edge guards (`Payment Complete`),
and item flows as lines connecting the boxes.

### 3.4 What this example shows

- **Episode → nested function**: `Order Intake` / `Drink Preparation` each have their own `start … done`.
- **fork/join concurrency**: in `Drink Preparation`, `Make Drink ∥ Preheat Cup` run in parallel and join before `Serve`.
- **Guarded decision**: `Payment Complete` Boolean + `if 'Payment Complete' == true` succession.
- **item flow**: `Order Slip` is produced (out) in ep1 → consumed (in) in ep2, a 3-level `flow` across the boundary.
- **allocate**: each action is allocated to a performer.

## 4. Mapping rules (summary)

| T2A-ESS slot / relation | EFFBD SysML |
|---|---|
| `performers[]` | `#Performer part '<label>' : Performer;` |
| `scenarios[0]` | root `#Function action '<label>' { … }` |
| `episodes[]` (`has_episode`, `contains_action`) | nested `#Function action '<episode>' { … }`; scenario-level `start→ep1→…→done` |
| `actions[]` | `#Function action '<label>';` inside the owning episode |
| `performed_by` | `allocate '<action>' to '<performer>';` |
| `produces_item` | `out item '<item>' : ItemOutputEdge;` of that action |
| `uses_item` / `provided_to` | `in item '<item>' : ItemInputEdge;` of that action |
| `flows`(source/target) · `temporal_before` | `succession first '<A>' then '<B>';` |
| unguarded multiple outgoing/incoming | `fork`/`join` (`New Start/End Concurrency_N`) |
| `controls`(`controls_flow`)·`guard_texts` | `attribute '<guard>' : ScalarValues::Boolean;` + `succession … if '<guard>' == true then …` |
| `flows`(object)·`carries_item` | `flow from '<A>'.'<item>' to '<B>'.'<item>';` (3-level when crossing a boundary) |

Element names use, as-is, the **quoted labels** that the EFFBD editor uses as keys (duplicates are made unique with a suffix).

Member names within one namespace (SysML v2 namespace) must be distinct from each other (otherwise LSP `Duplicate definition`),
so ` #k` (k = 2, 3, …) is appended only when there is a collision. The output for inputs without collisions is unchanged.

| Collision | Handling |
|---|---|
| An action uses and produces the same item (relay) — `in`/`out` ports with the same name | The output port becomes `out item '<item> #k' :> '<root>'::'<item>';`. The payload is specified by subsetting and no type is attached (the editor does not read the payload from a `: ItemOutputEdge`-typed port and falls back to the port name). Any `flow` leaving that port references the new name |
| A guard attribute has the same name as an action (an item, if flat) of the same function | The attribute becomes `'<guard> #k'` (the `if` reference in the succession changes with it) |
| An episode has the same name as an item of the root function or another episode | The episode becomes `'<label> #k'` (the episode sequencing and 3-level flow paths change with it) |
| In a flat function, an action has the same name as an item | The action becomes `'<label> #k'` |

## 5. Architecture

```text
src/
  convert_t2a_to_sysml.py   CLI (json -> .sysml, --validate/--validate-only/--state/--no-imm-tags)
  t2a_sysml/
    model.py                T2A-ESS loading + slot/relation index (slot_relations graph queries)
    converter.py            slots -> EFFBD SysML (nesting/fork-join/guard/flow)
    state_converter.py      state axis -> standard SysML v2 state def (State View)
    validate.py             schema validation (`validate_schema`, Slot Relation contract) + EFFBD structure validation (references·reachability·item flow)
  examples/                 coffee_order_T2A-ESS.json + coffee_order.sysml + coffee_order.state.sysml
```

Core flow (`converter.py`):
1. Label→unique name mapping (`_unique_labels`).
2. Episode grouping (`_episode_groups`) — nested if coverage is complete, otherwise flat fallback.
3. Per-group emission (`_emit_group`): actions+item ports → fork/join inference (`_control_flow`) → guard
   attributes → allocate → succession.
4. Scenario level: episode sequencing + cross-episode item flow.

### Programmatic use (Python API)

```python
import sys; sys.path.insert(0, "src")
from t2a_sysml import load_model, convert_file, validate_effbd, summarize

sysml = convert_file("path/to.json")            # default EFFBD (IMM tags)
sysml_plain = convert_file("path/to.json", imm_tags=False)

model = load_model("path/to.json")
issues = validate_effbd(model)                  # list of structural issues
print(summarize(issues))                        # {"ok": True, "errors": 0, "warnings": N}
```

### 5.1 State View (`--state`)

The state axis (situations/state_values/transitions/events/constraints) is emitted as a separate view
in **standard SysML v2** `state def` text (no IMM tags; SysML-v2-Release
training/23 style). Coffee example (`--state`) output:

```sysml
package 'Cafe Order Processing Example' {
    private import ScalarValues::*;

    // Cafe Order Processing Example
    // Generated from T2A-ESS by t2a_sysml.state.v0.1

    // events that trigger transitions (accept payloads)
    attribute def 'Payment Approved';
    attribute def 'Order Slip Received';
    attribute def 'Drink Completed';

    state def 'Coffee Order Scenario' {
        // guards (constrained_by on transitions)
        attribute 'Payment Within 3 Minutes' : Boolean;

        state 'order_status' {
            entry; then 'Order Waiting State';

            // has_situation: Order Intake
            state 'Order Waiting State' {
                doc /* order_status = waiting; queue_length = 0 orders */
            }
            // has_situation: Order Intake
            state 'Payment Complete State' {
                doc /* order_status = paid */
            }
            // has_situation: Drink Preparation
            state 'Making State' {
                doc /* order_status = making */
            }
            // has_situation: Drink Preparation
            state 'Served State' {
                doc /* order_status = served */
            }

            transition 'Transition from Order Waiting to Payment Complete'
                first 'Order Waiting State'
                accept 'Payment Approved'
                if 'Payment Within 3 Minutes'
                do action 'Payment'
                then 'Payment Complete State';
            transition 'Transition from Payment Complete to Making'
                first 'Payment Complete State'
                accept 'Order Slip Received'
                then 'Making State';
            transition 'Transition from Making to Served'
                first 'Making State'
                accept 'Drink Completed'
                do action 'Serve'
                then 'Served State';
        }
    }
}
```

Mapping: situation→`state`, `has_state_value`→`variable = value [unit]` inside `doc`,
transition→`transition … first … then`, `triggers`(Event)→`accept`+`attribute def`,
`constrained_by`(Transition→Constraint)→`attribute : Boolean`+`if`,
`causes`(Action→Transition)→`do action`, `has_situation`→`//` comment. Regions are
the connected components of the from/to_situation transition graph (`parallel` if there are 2 or more), and the initial state is
the state that has no incoming transition and whose owning episode has the earliest `order_index`.

Since this view is standard SysML v2, selab-rust-lsp parses it as-is — apart from the known
`entry; then` severity-2 warning ("succession declares only one end", an LSP quirk),
there are no error diagnostics (regression-guarded by the kind `state` check in `tools/lsp_check.js`).

The JS side also renders the same graph as a UML state diagram HTML (self-contained page,
no external libraries): `node src/t2a_js/tools/state_diagram.js <t2a-ess.json> -o
out.state.html` or CLI `--state-html PATH`. Example: `src/examples/coffee_order.state.html`.

## 6. Validation

- **Structure validator (`--validate`)**: in-repo. `validate_schema` schema checks (Slot Relation contract;
  UNKNOWN_RELATION_TYPE / RELATION_ENDPOINT_TYPE / DANGLING_RELATION_ENDPOINT /
  TRANSITION_ENDPOINTS = `error`) + EFFBD structure checks (unreachable action·dangling endpoint =
  `error`, item that is only produced/only consumed = `warning` ITEM_NO_CONSUMER/PRODUCER).
- All 3 golds (MUM-T/NGHE/autonomous driving) have `errors=0`.

> **Runtime validation caveat**: for the EFFBD SysML dialect, the **editor's IMM environment** is the validator. The standard SysML v2
> Pilot parser is not a validator for this dialect (even the editor's real examples fail in Pilot). text2effbd's
> headless compiler is a blueprint→SysML **generator**, so it cannot be used for SysML validation. Final runtime
> validation is done by loading the `.sysml` into selab-effbd-editor.

## 7. Known limitations / trade-offs

- **Absorption of inter-episode control flow**: action→action edges that cross episode boundaries and their decision
  guards are not represented individually but are collapsed into `epX → epY` sequencing. (Preserving guards across boundaries is future work.)
- **No decide/merge nodes generated**: decisions are expressed as guarded successions. Multi-branch `decide` nodes
  need more branch-set data, because T2A gives only a single flow per control.
- `constraints`→condition and `goals`→requirement are future work.
- If there is no episode coverage, it automatically falls back to a **flat root function**.

## 8. Tests

```powershell
python -m unittest discover -s tests -p "test_*.py"   # 7 passed
```
`test_t2a_sysml.py`: EFFBD structure · plain form · all golds · controls guards · episode nesting ·
structure validator · non-gold fallback.
