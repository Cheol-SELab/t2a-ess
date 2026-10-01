# T2A-ESS Relationship Traceability Report

This report is generated from T2A-ESS JSON files. It checks relationship endpoints, source traceability, graph connectivity, and selected semantic completeness indicators.

| File | Source Units | Slots | Slot Relations | Graph Edges |
| --- | --- | --- | --- | --- |
| mumt.nongold.json | 11 | 90 | 48 | 116 |

## mumt.nongold.json

- Model: MUM-T attack maneuver unstructured test text T2A-ESS extraction result

| Slot Type | Count |
| --- | --- |
| Scenario | 1 |
| Episode | 4 |
| Situation | 4 |
| StateValue | 7 |
| Observation | 6 |
| Event | 7 |
| Transition | 5 |
| Performer | 9 |
| Action | 14 |
| Item | 6 |
| Flow | 8 |
| Control | 3 |
| Constraint | 5 |
| Goal | 3 |
| Reason | 3 |
| DomainExtensionRule | 2 |
| SemanticBinding | 3 |

| Relation Type | Count |
| --- | --- |
| has_episode | 4 |
| from_situation | 4 |
| to_situation | 4 |
| triggers | 4 |
| observes | 4 |
| contains_performer | 3 |
| has_state_value | 3 |
| produces_item | 3 |
| has_goal | 3 |
| has_reason | 3 |
| temporal_before | 3 |
| performed_by | 2 |
| flow_source | 2 |
| controls_flow | 2 |
| binds_to | 2 |
| flow_target | 1 |
| carries_item | 1 |

### Mermaid Relationship Graph

- Mode: `slot_relations`. Rendered edges: `48`. Omitted edges: `0`.

```mermaid
flowchart LR
  N0001["Action<br/>MUMT_A_ACTIVATE_LOCAL_SURVIVAL<br/>Activate local sensor-based survival loop"]
  N0002["Action<br/>MUMT_A_ALERT_FPV<br/>Provide FPV threat alert"]
  N0003["Action<br/>MUMT_A_DECIDE_DETOUR<br/>Decide right bypass maneuver"]
  N0004["Action<br/>MUMT_A_DISPERSE_COMMAND<br/>Order dispersed maneuver and air-defense watch"]
  N0005["Action<br/>MUMT_A_DRONE_LAUNCH<br/>Sequential reconnaissance drone launch and surveilla..."]
  N0006["Action<br/>MUMT_A_EMERGENCY_BROADCAST<br/>Transmit drone emergency broadcast"]
  N0007["Action<br/>MUMT_A_RESUME_ATTACK<br/>Resume attack maneuver"]
  N0008["Action<br/>MUMT_A_SWITCH_EDGE_MODE<br/>Drone switch to Edge AI analysis mode"]
  N0009["Action<br/>MUMT_A_TDSS_DIAGNOSE<br/>TDSS self-diagnosis and normal communication confirm..."]
  N0010["Control<br/>MUMT_CTRL_COMM_MODE_GUARD<br/>Communication mode transition guard"]
  N0011["Control<br/>MUMT_CTRL_LOCAL_SURVIVAL_LOOP<br/>Local survival loop during communication blackout"]
  N0012["Episode<br/>MUMT_EP_EW_DEGRADATION<br/>Electronic warfare jamming and communication degrada..."]
  N0013["Episode<br/>MUMT_EP_PREP_NORMAL<br/>Preparation and normal communication maneuver"]
  N0014["Episode<br/>MUMT_EP_RECOVERY_RESUME<br/>Communication recovery and attack resumption"]
  N0015["Episode<br/>MUMT_EP_THREAT_DETOUR<br/>Enemy observation post and FPV threat detection resp..."]
  N0016["Event<br/>MUMT_EVT_BANDWIDTH_RECOVERED<br/>Bandwidth recovery"]
  N0017["Event<br/>MUMT_EVT_HEARTBEAT_LOSS_PERSISTED<br/>Persistent heartbeat loss"]
  N0018["Event<br/>MUMT_EVT_LINK_STABLE<br/>Link kept stable"]
  N0019["Event<br/>MUMT_EVT_PACKET_LOSS_PERSISTED<br/>Packet loss rate persistently exceeds the threshold"]
  N0020["Flow<br/>MUMT_F_DISCONNECTED_TO_BROADCAST<br/>Drone emergency broadcast after blackout"]
  N0021["Flow<br/>MUMT_F_EDGE_MODE_TO_TRACK_FLOW<br/>Summary track transmission after Edge mode switch"]
  N0022["Flow<br/>MUMT_F_FPV_ALERT_TO_DISPERSE<br/>Dispersed maneuver after FPV alert"]
  N0023["Goal<br/>MUMT_G_MAINTAIN_MIN_SA<br/>Maintain minimum SA"]
  N0024["Goal<br/>MUMT_G_MAINTAIN_SURVIVABILITY<br/>Maintain survivability-focused functions"]
  N0025["Goal<br/>MUMT_G_SECURE_TARGET<br/>Secure objective"]
  N0026["Item<br/>MUMT_I_EMERGENCY_BROADCAST<br/>Drone emergency broadcast message"]
  N0027["Item<br/>MUMT_I_FPV_ALERT<br/>FPV threat alert"]
  N0028["Item<br/>MUMT_I_TRACK_SUMMARY<br/>Summary track data"]
  N0029["Observation<br/>MUMT_OBS_BANDWIDTH_RECOVERY<br/>Bandwidth recovery confirmed"]
  N0030["Observation<br/>MUMT_OBS_HEARTBEAT_LOSS<br/>Heartbeat loss detected"]
  N0031["Observation<br/>MUMT_OBS_LINK_RECOVERY<br/>Drone link recovery detected"]
  N0032["Observation<br/>MUMT_OBS_PACKET_LOSS<br/>Packet loss rate surge detected"]
  N0033["Performer<br/>MUMT_P2_TDSS<br/>TDSS"]
  N0034["Performer<br/>MUMT_P3_1_DRONE<br/>Drone 1"]
  N0035["Performer<br/>MUMT_P3_2_DRONE<br/>Drone 2"]
  N0036["Performer<br/>MUMT_P3_3_DRONE<br/>Drone 3"]
  N0037["Performer<br/>MUMT_P3_DRONE_TEAM<br/>Three reconnaissance drones"]
  N0038["Reason<br/>MUMT_R_DETOUR<br/>Bypass because of the possibility of anti-tank posit..."]
  N0039["Reason<br/>MUMT_R_GRACEFUL_DEGRADATION<br/>Perform graceful degradation because of communicatio..."]
  N0040["Reason<br/>MUMT_R_INDEPENDENT_SURVIVAL<br/>Continue independent action because integrated comma..."]
  N0041["SemanticBinding<br/>MUMT_SB_COMM_TRANSITIONS<br/>Binding communication mode transitions as StateTrans..."]
  N0042["SemanticBinding<br/>MUMT_SB_TRACK_DATA_ITEM<br/>Summary track data to SysML Item"]
  N0043["Scenario<br/>MUMT_SCN_ATTACK_OPERATION<br/>MUM-T-based attack maneuver and electronic warfare r..."]
  N0044["Situation<br/>MUMT_SIT_COMM_DISCONNECTED<br/>Communication blackout state"]
  N0045["Situation<br/>MUMT_SIT_COMM_LIMITED<br/>Limited communication state"]
  N0046["Situation<br/>MUMT_SIT_COMM_NORMAL<br/>Normal communication state"]
  N0047["StateValue<br/>MUMT_SV_COMM_DISCONNECTED<br/>disconnected"]
  N0048["StateValue<br/>MUMT_SV_COMM_LIMITED<br/>limited"]
  N0049["StateValue<br/>MUMT_SV_COMM_NORMAL<br/>normal"]
  N0050["Transition<br/>MUMT_TR_DISCONNECTED_TO_LIMITED<br/>Transition from communication blackout to limited co..."]
  N0051["Transition<br/>MUMT_TR_LIMITED_TO_DISCONNECTED<br/>Transition from limited communication to communicati..."]
  N0052["Transition<br/>MUMT_TR_LIMITED_TO_NORMAL<br/>Transition from limited communication to normal comm..."]
  N0053["Transition<br/>MUMT_TR_NORMAL_TO_LIMITED<br/>Transition from normal communication to limited comm..."]
  N0043 -->|has_episode| N0013
  N0043 -->|has_episode| N0015
  N0043 -->|has_episode| N0012
  N0043 -->|has_episode| N0014
  N0037 -->|contains_performer| N0034
  N0037 -->|contains_performer| N0035
  N0037 -->|contains_performer| N0036
  N0046 -->|has_state_value| N0049
  N0045 -->|has_state_value| N0048
  N0044 -->|has_state_value| N0047
  N0053 -->|from_situation| N0046
  N0053 -->|to_situation| N0045
  N0019 -->|triggers| N0053
  N0051 -->|from_situation| N0045
  N0051 -->|to_situation| N0044
  N0017 -->|triggers| N0051
  N0050 -->|from_situation| N0044
  N0050 -->|to_situation| N0045
  N0018 -->|triggers| N0050
  N0052 -->|from_situation| N0045
  N0052 -->|to_situation| N0046
  N0016 -->|triggers| N0052
  N0032 -->|observes| N0019
  N0030 -->|observes| N0017
  N0031 -->|observes| N0018
  N0029 -->|observes| N0016
  N0009 -->|performed_by| N0033
  N0005 -->|performed_by| N0037
  N0002 -->|produces_item| N0027
  N0008 -->|produces_item| N0028
  N0006 -->|produces_item| N0026
  N0022 -->|flow_source| N0002
  N0022 -->|flow_target| N0004
  N0021 -->|flow_source| N0008
  N0021 -->|carries_item| N0028
  N0010 -->|controls_flow| N0021
  N0011 -->|controls_flow| N0020
  N0008 -->|has_goal| N0023
  N0001 -->|has_goal| N0024
  N0007 -->|has_goal| N0025
  N0003 -->|has_reason| N0038
  N0008 -->|has_reason| N0039
  N0001 -->|has_reason| N0040
  N0041 -->|binds_to| N0053
  N0042 -->|binds_to| N0028
  N0053 -->|temporal_before| N0051
  N0051 -->|temporal_before| N0050
  N0050 -->|temporal_before| N0052
  classDef SourceUnit fill:#F6F8FA,stroke:#8A8A8A,stroke-width:1px,color:#111;
  classDef Scenario fill:#DDEBFF,stroke:#5A78B8,stroke-width:1px,color:#111;
  classDef Episode fill:#E7F0FF,stroke:#5A78B8,stroke-width:1px,color:#111;
  classDef Action fill:#E8F5E9,stroke:#4C8A4C,stroke-width:1px,color:#111;
  classDef Performer fill:#FFF4D6,stroke:#9A7A2F,stroke-width:1px,color:#111;
  classDef Event fill:#FFE3E3,stroke:#B45A5A,stroke-width:1px,color:#111;
  classDef Transition fill:#FFD6D6,stroke:#B45A5A,stroke-width:1px,color:#111;
  classDef Situation fill:#EFE6FF,stroke:#7B5AB8,stroke-width:1px,color:#111;
  classDef StateValue fill:#F5ECFF,stroke:#7B5AB8,stroke-width:1px,color:#111;
  classDef Flow fill:#E0F7FA,stroke:#438A91,stroke-width:1px,color:#111;
  classDef Control fill:#E0F2F1,stroke:#438A75,stroke-width:1px,color:#111;
  classDef Constraint fill:#FCE4EC,stroke:#A35272,stroke-width:1px,color:#111;
  classDef Goal fill:#E8EAF6,stroke:#5A62A8,stroke-width:1px,color:#111;
  classDef Reason fill:#FFF8E1,stroke:#9A7A2F,stroke-width:1px,color:#111;
  classDef Item fill:#F1F8E9,stroke:#6B8A3A,stroke-width:1px,color:#111;
  classDef DomainExtensionRule fill:#ECEFF1,stroke:#607D8B,stroke-width:1px,color:#111;
  classDef SemanticBinding fill:#ECEFF1,stroke:#607D8B,stroke-width:1px,color:#111;
  class N0001,N0002,N0003,N0004,N0005,N0006,N0007,N0008,N0009 Action;
  class N0010,N0011 Control;
  class N0012,N0013,N0014,N0015 Episode;
  class N0016,N0017,N0018,N0019 Event;
  class N0020,N0021,N0022 Flow;
  class N0023,N0024,N0025 Goal;
  class N0026,N0027,N0028 Item;
  class N0033,N0034,N0035,N0036,N0037 Performer;
  class N0038,N0039,N0040 Reason;
  class N0043 Scenario;
  class N0041,N0042 SemanticBinding;
  class N0044,N0045,N0046 Situation;
  class N0047,N0048,N0049 StateValue;
  class N0050,N0051,N0052,N0053 Transition;
```

| Check | Count | Examples |
| --- | --- | --- |
| Duplicate IDs | 0 | - |
| Missing IDs | 0 | - |
| Dangling Slot Relations | 0 | - |
| Dangling Source Refs | 0 | - |
| Source Units Without Slots | 0 | - |
| Slots Without Source Ref | 22 | MUMT_A_AVOID_FPV, MUMT_A_EMERGENCY_BROADCAST, MUMT_A_REPORT_BATTALION, MUMT_A_RESUME_ATTACK, MUMT_A_SMOKE_EVASION, MUMT_CTRL_RECOVERY_STAGED, MUMT_DER_THREAT_TYPES, MUMT_EVT_ATGM_LAUNCH, MUMT_F_ATGM_ALERT_TO_EVASION, MUMT_F_DISCONNECTED_TO_BROADCAST, MUMT_F_NORMAL_RESTORED_TO_ATTACK, MUMT_G_SECURE_TARGET, MUMT_I_BATTLE_REPORT, MUMT_I_EMERGENCY_BROADCAST, MUMT_R_INDEPENDENT_SURVIVAL, MUMT_SB_COMM_TRANSITIONS, MUMT_SB_TDSS_PART, MUMT_SB_TRACK_DATA_ITEM, MUMT_SIT_MISSION_SECURED, MUMT_SV_AVAILABLE_DRONES_2 ... (+2) |
| Isolated Slots | 37 | MUMT_A_AVOID_FPV, MUMT_A_DETECT_OBSERVATION_POST, MUMT_A_REPORT_BATTALION, MUMT_A_RESYNC_SA, MUMT_A_SMOKE_EVASION, MUMT_CTRL_RECOVERY_STAGED, MUMT_C_FPV_ETA, MUMT_C_HEARTBEAT_TIMEOUT, MUMT_C_LINK_STABILITY, MUMT_C_PACKET_LOSS_THRESHOLD, MUMT_C_SURVIVABILITY_PRIORITY, MUMT_DER_COMM_DEGRADATION, MUMT_DER_THREAT_TYPES, MUMT_EVT_ATGM_LAUNCH, MUMT_EVT_EW_JAMMING_START, MUMT_EVT_FPV_APPROACH, MUMT_F_ATGM_ALERT_TO_EVASION, MUMT_F_LINK_RECOVERY_TO_RESYNC, MUMT_F_NORMAL_RESTORED_TO_ATTACK, MUMT_F_OP_DETECT_TO_DETOUR ... (+17) |
| Actions With Actor Text But No Performer Relation | 12 | MUMT_A_ACTIVATE_LOCAL_SURVIVAL, MUMT_A_ALERT_FPV, MUMT_A_AVOID_FPV, MUMT_A_DECIDE_DETOUR, MUMT_A_DETECT_OBSERVATION_POST, MUMT_A_DISPERSE_COMMAND, MUMT_A_EMERGENCY_BROADCAST, MUMT_A_REPORT_BATTALION, MUMT_A_RESUME_ATTACK, MUMT_A_RESYNC_SA, MUMT_A_SMOKE_EVASION, MUMT_A_SWITCH_EDGE_MODE |
| Transitions Missing from_situation | 1 | MUMT_TR_DRONE_COUNT_REDUCED |
| Transitions Missing to_situation | 1 | MUMT_TR_DRONE_COUNT_REDUCED |
| Transitions Missing trigger | 1 | MUMT_TR_DRONE_COUNT_REDUCED |
| Flows Missing source | 6 | MUMT_F_ATGM_ALERT_TO_EVASION, MUMT_F_DISCONNECTED_TO_BROADCAST, MUMT_F_LINK_RECOVERY_TO_RESYNC, MUMT_F_NORMAL_RESTORED_TO_ATTACK, MUMT_F_OP_DETECT_TO_DETOUR, MUMT_F_PREP_TO_DRONE_LAUNCH |
| Flows Missing target | 7 | MUMT_F_ATGM_ALERT_TO_EVASION, MUMT_F_DISCONNECTED_TO_BROADCAST, MUMT_F_EDGE_MODE_TO_TRACK_FLOW, MUMT_F_LINK_RECOVERY_TO_RESYNC, MUMT_F_NORMAL_RESTORED_TO_ATTACK, MUMT_F_OP_DETECT_TO_DETOUR, MUMT_F_PREP_TO_DRONE_LAUNCH |

### Example Source Trace: `MUMT_L03`
| Depth | Dir | Relation | Node | Type | Label |
| --- | --- | --- | --- | --- | --- |
| 1 | out | source_ref | MUMT_P1_COMMANDER | Performer | Company commander |
| 1 | out | source_ref | MUMT_SCN_ATTACK_OPERATION | Scenario | MUM-T-based attack maneuver and electronic warfare response |

