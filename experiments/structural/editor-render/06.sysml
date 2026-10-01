private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// NGHE autonomous construction unstructured test text T2A-ESS extraction result
// Generated from T2A-ESS by t2a_sysml.effbd.v0.3

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
part 'DMSS' : Performer;
#Performer
part 'ASPCS' : Performer;

#Function
action 'NGHE 72 h autonomous construction and contingency response' {
    #Function
    action 'Energy infrastructure installation and battery pack stockpiling';
    #Function
    action 'RTDD latency and HSM authentication confirmation';
    #Function
    action '3D point cloud scan and reference point correction';
    #Function
    action 'Authentication and calibration of 19 units of equipment';
    #Function
    action 'Autonomous construction start';
    #Function
    action 'Battery pack replacement' {
        in item 'Battery pack' : ItemInputEdge;
    }
    #Function
    action 'Battery swap sequence optimization';
    #Function
    action 'U-EDT Unit 7 hydraulic module preventive maintenance';
    #Function
    action 'OTA route optimization patch application';
    #Function
    action 'Level 3 downgrade proposal and approval due to fog';
    #Function
    action 'External public network blocking and switch to internal security network';
    #Function
    action 'Forced work stop and safe evacuation';
    #Function
    action 'Terrain rescan and reference point re-correction after heavy rain' {
        out item '3D point cloud terrain data' : ItemOutputEdge;
    }
    #Function
    action 'Subsidence zone bypass route recalculation' {
        out item 'Work routes and bypass routes' : ItemOutputEdge;
    }
    #Function
    action 'Construction resumption and return to Level 4';
    #Function
    action 'Automatic generation of 72 h mission final report' {
        out item 'Comprehensive performance report' : ItemOutputEdge;
    }

    fork 'New Start Concurrency_1';
    join 'New End Concurrency_1';

    allocate 'Energy infrastructure installation and battery pack stockpiling' to 'Site maintenance team';
    allocate 'RTDD latency and HSM authentication confirmation' to 'Site supervisor';
    allocate '3D point cloud scan and reference point correction' to 'DMSS';
    allocate 'Authentication and calibration of 19 units of equipment' to 'Unmanned equipment fleet';
    allocate 'Battery pack replacement' to 'BSS_T';

    succession first start then 'New Start Concurrency_1';
    succession first 'Energy infrastructure installation and battery pack stockpiling' then 'New End Concurrency_1';
    succession first 'RTDD latency and HSM authentication confirmation' then 'New End Concurrency_1';
    succession first '3D point cloud scan and reference point correction' then 'New End Concurrency_1';
    succession first 'Authentication and calibration of 19 units of equipment' then 'New End Concurrency_1';
    succession first 'Autonomous construction start' then 'New End Concurrency_1';
    succession first 'Battery pack replacement' then 'New End Concurrency_1';
    succession first 'Battery swap sequence optimization' then 'New End Concurrency_1';
    succession first 'U-EDT Unit 7 hydraulic module preventive maintenance' then 'New End Concurrency_1';
    succession first 'OTA route optimization patch application' then 'New End Concurrency_1';
    succession first 'Level 3 downgrade proposal and approval due to fog' then 'New End Concurrency_1';
    succession first 'External public network blocking and switch to internal security network' then 'New End Concurrency_1';
    succession first 'Forced work stop and safe evacuation' then 'New End Concurrency_1';
    succession first 'Terrain rescan and reference point re-correction after heavy rain' then 'New End Concurrency_1';
    succession first 'Subsidence zone bypass route recalculation' then 'New End Concurrency_1';
    succession first 'Construction resumption and return to Level 4' then 'New End Concurrency_1';
    succession first 'Automatic generation of 72 h mission final report' then 'New End Concurrency_1';
    succession first 'New Start Concurrency_1' then 'Energy infrastructure installation and battery pack stockpiling';
    succession first 'New Start Concurrency_1' then 'RTDD latency and HSM authentication confirmation';
    succession first 'New Start Concurrency_1' then '3D point cloud scan and reference point correction';
    succession first 'New Start Concurrency_1' then 'Authentication and calibration of 19 units of equipment';
    succession first 'New Start Concurrency_1' then 'Autonomous construction start';
    succession first 'New Start Concurrency_1' then 'Battery pack replacement';
    succession first 'New Start Concurrency_1' then 'Battery swap sequence optimization';
    succession first 'New Start Concurrency_1' then 'U-EDT Unit 7 hydraulic module preventive maintenance';
    succession first 'New Start Concurrency_1' then 'OTA route optimization patch application';
    succession first 'New Start Concurrency_1' then 'Level 3 downgrade proposal and approval due to fog';
    succession first 'New Start Concurrency_1' then 'External public network blocking and switch to internal security network';
    succession first 'New Start Concurrency_1' then 'Forced work stop and safe evacuation';
    succession first 'New Start Concurrency_1' then 'Terrain rescan and reference point re-correction after heavy rain';
    succession first 'New Start Concurrency_1' then 'Subsidence zone bypass route recalculation';
    succession first 'New Start Concurrency_1' then 'Construction resumption and return to Level 4';
    succession first 'New Start Concurrency_1' then 'Automatic generation of 72 h mission final report';
    succession first 'New End Concurrency_1' then done;

    item 'Battery pack';
    item '3D point cloud terrain data';
    item 'Work routes and bypass routes';
    item 'Comprehensive performance report';
}
