private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// NGHE autonomous construction unstructured test text T2A-ESS exhaustive extraction result
// Generated from T2A-ESS by t2a_sysml.effbd.v0.3

#Performer
part 'Company A' : Performer;
#Performer
part 'ICCC' : Performer;
#Performer
part 'AI_ICP' : Performer;
#Performer
part 'Remote supervisor' : Performer;
#Performer
part 'Remote operator' : Performer;
#Performer
part 'Site supervisor' : Performer;
#Performer
part 'Site maintenance team' : Performer;
#Performer
part 'Unmanned equipment fleet' : Performer;
#Performer
part 'U-EEX excavator' : Performer;
#Performer
part 'U-EDT dump truck' : Performer;
#Performer
part 'U-EDB bulldozer' : Performer;
#Performer
part 'U-ERC roller' : Performer;
#Performer
part 'BSS_T' : Performer;
#Performer
part 'ESS_T' : Performer;
#Performer
part 'SCS' : Performer;
#Performer
part 'DMSS' : Performer;
#Performer
part 'ASPCS' : Performer;
#Performer
part 'Security system' : Performer;
#Performer
part 'Onboard system' : Performer;

#Function
action 'NGHE 72 h autonomous construction full scenario' {
    #Function
    action 'Set 72 h mission goals';
    #Function
    action 'Install energy infrastructure';
    #Function
    action 'Stockpile fully charged battery packs' {
        in item 'Fully charged battery packs' : ItemInputEdge;
    }
    #Function
    action 'Confirm RTDD latency';
    #Function
    action 'Confirm HSM authentication';
    #Function
    action '3D point cloud terrain scan' {
        out item '3D point cloud terrain data' : ItemOutputEdge;
    }
    #Function
    action 'Correct GPS-RTK reference points';
    #Function
    action 'Reflect in BIM/digital twin initial model' {
        out item 'BIM/digital twin model' : ItemOutputEdge;
    }
    #Function
    action 'Approve Level 3 start';
    #Function
    action 'Sequential offloading of 19 units of equipment';
    #Function
    action 'Equipment authentication and calibration';
    #Function
    action 'Confirm Keep-out Zone';
    #Function
    action 'Allocate excavation points, quotas, optimal routes' {
        out item 'Work routes and bypass routes' : ItemOutputEdge;
    }
    #Function
    action 'Excavation and loading';
    #Function
    action 'Hauling to the unloading area';
    #Function
    action 'Soil grading';
    #Function
    action 'Operation data review before Level 4 transition';
    #Function
    action 'Level 4 transition approval';
    #Function
    action 'Autonomous adjustment of process planning, equipment allocation, route updates';
    #Function
    action 'Remote operator shift handover';
    #Function
    action 'Operator fatigue monitoring';
    #Function
    action 'Enter Eco Mode';
    #Function
    action 'Autonomous return to BSS_T';
    #Function
    action 'Battery pack replacement';
    #Function
    action 'Swap sequence optimization';
    #Function
    action 'Generate automatic performance report' {
        out item 'Automatic performance report' : ItemOutputEdge;
    }
    #Function
    action 'PHM anomaly sign detection';
    #Function
    action 'U-EDT Unit 7 non-core route reassignment';
    #Function
    action 'Hydraulic module replacement' {
        in item 'Hydraulic module' : ItemInputEdge;
    }
    #Function
    action 'OTA route optimization patch application' {
        in item 'Route optimization algorithm patch' : ItemInputEdge;
    }
    #Function
    action 'Perform ground compaction';
    #Function
    action 'Level 3 downgrade proposal due to fog';
    #Function
    action 'Approve Level 3 downgrade';
    #Function
    action 'Raise radar/ultrasonic sensor priority';
    #Function
    action 'Detect forged command packet' {
        in item 'Command packet' : ItemInputEdge;
    }
    #Function
    action 'Block external public network';
    #Function
    action 'Switch to internal closed security network';
    #Function
    action 'Approve return to Level 4 after fog clears';
    #Function
    action 'Establish heavy rain preparation plan';
    #Function
    action 'Autonomous attempt to remove sensor contamination';
    #Function
    action 'Full stop after pedestrian detection';
    #Function
    action 'Issue forced work stop command';
    #Function
    action 'Move to and wait at safe evacuation positions';
    #Function
    action 'Rescan terrain after heavy rain';
    #Function
    action 'Re-correct GPS-RTK reference points';
    #Function
    action 'Subsidence zone bypass route recalculation';
    #Function
    action 'Approve Level 3 construction resumption';
    #Function
    action 'Return to work area';
    #Function
    action 'Approve Level 4 transition after recovery';
    #Function
    action 'Adjust compaction pressure and number of passes in moisture content change sections';
    #Function
    action 'Generate final performance report' {
        out item 'Final performance report' : ItemOutputEdge;
    }

    fork 'New Start Concurrency_1';
    join 'New End Concurrency_1';

    attribute 'Prevent 2 or more units leaving work simultaneously' : ScalarValues::Boolean;  // control: scheduling_guard
    attribute 'Digital signature forgery detection' : ScalarValues::Boolean;  // control: decision
    attribute 'Heavy rain intensifies' : ScalarValues::Boolean;  // control: decision


    succession first start then 'New Start Concurrency_1';
    succession first 'Enter Eco Mode' if 'Prevent 2 or more units leaving work simultaneously' == true then 'Battery pack replacement';
    succession first 'Detect forged command packet' if 'Digital signature forgery detection' == true then 'Switch to internal closed security network';
    succession first 'Issue forced work stop command' if 'Heavy rain intensifies' == true then 'Move to and wait at safe evacuation positions';
    succession first 'Set 72 h mission goals' then 'New End Concurrency_1';
    succession first 'Install energy infrastructure' then 'New End Concurrency_1';
    succession first 'Stockpile fully charged battery packs' then 'New End Concurrency_1';
    succession first 'Confirm RTDD latency' then 'New End Concurrency_1';
    succession first 'Confirm HSM authentication' then 'New End Concurrency_1';
    succession first '3D point cloud terrain scan' then 'New End Concurrency_1';
    succession first 'Correct GPS-RTK reference points' then 'New End Concurrency_1';
    succession first 'Reflect in BIM/digital twin initial model' then 'New End Concurrency_1';
    succession first 'Approve Level 3 start' then 'New End Concurrency_1';
    succession first 'Sequential offloading of 19 units of equipment' then 'New End Concurrency_1';
    succession first 'Equipment authentication and calibration' then 'New End Concurrency_1';
    succession first 'Confirm Keep-out Zone' then 'New End Concurrency_1';
    succession first 'Allocate excavation points, quotas, optimal routes' then 'New End Concurrency_1';
    succession first 'Excavation and loading' then 'New End Concurrency_1';
    succession first 'Hauling to the unloading area' then 'New End Concurrency_1';
    succession first 'Soil grading' then 'New End Concurrency_1';
    succession first 'Operation data review before Level 4 transition' then 'New End Concurrency_1';
    succession first 'Level 4 transition approval' then 'New End Concurrency_1';
    succession first 'Autonomous adjustment of process planning, equipment allocation, route updates' then 'New End Concurrency_1';
    succession first 'Remote operator shift handover' then 'New End Concurrency_1';
    succession first 'Operator fatigue monitoring' then 'New End Concurrency_1';
    succession first 'Autonomous return to BSS_T' then 'New End Concurrency_1';
    succession first 'Battery pack replacement' then 'New End Concurrency_1';
    succession first 'Swap sequence optimization' then 'New End Concurrency_1';
    succession first 'Generate automatic performance report' then 'New End Concurrency_1';
    succession first 'PHM anomaly sign detection' then 'New End Concurrency_1';
    succession first 'U-EDT Unit 7 non-core route reassignment' then 'New End Concurrency_1';
    succession first 'Hydraulic module replacement' then 'New End Concurrency_1';
    succession first 'OTA route optimization patch application' then 'New End Concurrency_1';
    succession first 'Perform ground compaction' then 'New End Concurrency_1';
    succession first 'Level 3 downgrade proposal due to fog' then 'New End Concurrency_1';
    succession first 'Approve Level 3 downgrade' then 'New End Concurrency_1';
    succession first 'Raise radar/ultrasonic sensor priority' then 'New End Concurrency_1';
    succession first 'Block external public network' then 'New End Concurrency_1';
    succession first 'Switch to internal closed security network' then 'New End Concurrency_1';
    succession first 'Approve return to Level 4 after fog clears' then 'New End Concurrency_1';
    succession first 'Establish heavy rain preparation plan' then 'New End Concurrency_1';
    succession first 'Autonomous attempt to remove sensor contamination' then 'New End Concurrency_1';
    succession first 'Full stop after pedestrian detection' then 'New End Concurrency_1';
    succession first 'Move to and wait at safe evacuation positions' then 'New End Concurrency_1';
    succession first 'Rescan terrain after heavy rain' then 'New End Concurrency_1';
    succession first 'Re-correct GPS-RTK reference points' then 'New End Concurrency_1';
    succession first 'Subsidence zone bypass route recalculation' then 'New End Concurrency_1';
    succession first 'Approve Level 3 construction resumption' then 'New End Concurrency_1';
    succession first 'Return to work area' then 'New End Concurrency_1';
    succession first 'Approve Level 4 transition after recovery' then 'New End Concurrency_1';
    succession first 'Adjust compaction pressure and number of passes in moisture content change sections' then 'New End Concurrency_1';
    succession first 'Generate final performance report' then 'New End Concurrency_1';
    succession first 'New Start Concurrency_1' then 'Set 72 h mission goals';
    succession first 'New Start Concurrency_1' then 'Install energy infrastructure';
    succession first 'New Start Concurrency_1' then 'Stockpile fully charged battery packs';
    succession first 'New Start Concurrency_1' then 'Confirm RTDD latency';
    succession first 'New Start Concurrency_1' then 'Confirm HSM authentication';
    succession first 'New Start Concurrency_1' then '3D point cloud terrain scan';
    succession first 'New Start Concurrency_1' then 'Correct GPS-RTK reference points';
    succession first 'New Start Concurrency_1' then 'Reflect in BIM/digital twin initial model';
    succession first 'New Start Concurrency_1' then 'Approve Level 3 start';
    succession first 'New Start Concurrency_1' then 'Sequential offloading of 19 units of equipment';
    succession first 'New Start Concurrency_1' then 'Equipment authentication and calibration';
    succession first 'New Start Concurrency_1' then 'Confirm Keep-out Zone';
    succession first 'New Start Concurrency_1' then 'Allocate excavation points, quotas, optimal routes';
    succession first 'New Start Concurrency_1' then 'Excavation and loading';
    succession first 'New Start Concurrency_1' then 'Hauling to the unloading area';
    succession first 'New Start Concurrency_1' then 'Soil grading';
    succession first 'New Start Concurrency_1' then 'Operation data review before Level 4 transition';
    succession first 'New Start Concurrency_1' then 'Level 4 transition approval';
    succession first 'New Start Concurrency_1' then 'Autonomous adjustment of process planning, equipment allocation, route updates';
    succession first 'New Start Concurrency_1' then 'Remote operator shift handover';
    succession first 'New Start Concurrency_1' then 'Operator fatigue monitoring';
    succession first 'New Start Concurrency_1' then 'Enter Eco Mode';
    succession first 'New Start Concurrency_1' then 'Autonomous return to BSS_T';
    succession first 'New Start Concurrency_1' then 'Swap sequence optimization';
    succession first 'New Start Concurrency_1' then 'Generate automatic performance report';
    succession first 'New Start Concurrency_1' then 'PHM anomaly sign detection';
    succession first 'New Start Concurrency_1' then 'U-EDT Unit 7 non-core route reassignment';
    succession first 'New Start Concurrency_1' then 'Hydraulic module replacement';
    succession first 'New Start Concurrency_1' then 'OTA route optimization patch application';
    succession first 'New Start Concurrency_1' then 'Perform ground compaction';
    succession first 'New Start Concurrency_1' then 'Level 3 downgrade proposal due to fog';
    succession first 'New Start Concurrency_1' then 'Approve Level 3 downgrade';
    succession first 'New Start Concurrency_1' then 'Raise radar/ultrasonic sensor priority';
    succession first 'New Start Concurrency_1' then 'Detect forged command packet';
    succession first 'New Start Concurrency_1' then 'Block external public network';
    succession first 'New Start Concurrency_1' then 'Approve return to Level 4 after fog clears';
    succession first 'New Start Concurrency_1' then 'Establish heavy rain preparation plan';
    succession first 'New Start Concurrency_1' then 'Autonomous attempt to remove sensor contamination';
    succession first 'New Start Concurrency_1' then 'Full stop after pedestrian detection';
    succession first 'New Start Concurrency_1' then 'Issue forced work stop command';
    succession first 'New Start Concurrency_1' then 'Rescan terrain after heavy rain';
    succession first 'New Start Concurrency_1' then 'Re-correct GPS-RTK reference points';
    succession first 'New Start Concurrency_1' then 'Subsidence zone bypass route recalculation';
    succession first 'New Start Concurrency_1' then 'Approve Level 3 construction resumption';
    succession first 'New Start Concurrency_1' then 'Return to work area';
    succession first 'New Start Concurrency_1' then 'Approve Level 4 transition after recovery';
    succession first 'New Start Concurrency_1' then 'Adjust compaction pressure and number of passes in moisture content change sections';
    succession first 'New Start Concurrency_1' then 'Generate final performance report';
    succession first 'New End Concurrency_1' then done;

    item 'Fully charged battery packs';
    item '3D point cloud terrain data';
    item 'BIM/digital twin model';
    item 'Work routes and bypass routes';
    item 'Automatic performance report';
    item 'Hydraulic module';
    item 'Route optimization algorithm patch';
    item 'Command packet';
    item 'Final performance report';
}
