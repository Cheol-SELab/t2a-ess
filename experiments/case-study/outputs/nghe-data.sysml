private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// NGHE autonomous construction ground truth (relation closure) scenario
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
#Performer
part 'Security system' : Performer;
#Performer
part 'U-EEX Unit 1' : Performer;
#Performer
part 'U-EEX Unit 2' : Performer;
#Performer
part 'U-EEX Unit 3' : Performer;
#Performer
part 'U-EDT Unit 7' : Performer;

#Function
action 'NGHE 72 h autonomous construction and contingency response' {
    #Function
    action 'Site setup and Level 3 start' {
        #Function
        action 'Energy infrastructure installation and battery pack stockpiling' {
            out item 'Battery pack' : ItemOutputEdge;
        }
        #Function
        action 'RTDD latency and HSM authentication confirmation';
        #Function
        action '3D point cloud scan and reference point correction' {
            out item '3D point cloud terrain data' : ItemOutputEdge;
            out item 'BIM and digital twin model' : ItemOutputEdge;
        }
        #Function
        action 'Authentication and calibration of 19 units of equipment';

        fork 'New Start Concurrency_1';
        join 'New End Concurrency_1';

        allocate 'Energy infrastructure installation and battery pack stockpiling' to 'Site maintenance team';
        allocate 'RTDD latency and HSM authentication confirmation' to 'Site supervisor';
        allocate 'RTDD latency and HSM authentication confirmation' to 'ICCC';
        allocate '3D point cloud scan and reference point correction' to 'DMSS';
        allocate '3D point cloud scan and reference point correction' to 'ASPCS';
        allocate 'Authentication and calibration of 19 units of equipment' to 'Unmanned equipment fleet';

        succession first start then 'New Start Concurrency_1';
        succession first 'Energy infrastructure installation and battery pack stockpiling' then 'New End Concurrency_1';
        succession first 'RTDD latency and HSM authentication confirmation' then 'New End Concurrency_1';
        succession first '3D point cloud scan and reference point correction' then 'New End Concurrency_1';
        succession first 'Authentication and calibration of 19 units of equipment' then 'New End Concurrency_1';
        succession first 'New Start Concurrency_1' then 'Energy infrastructure installation and battery pack stockpiling';
        succession first 'New Start Concurrency_1' then 'RTDD latency and HSM authentication confirmation';
        succession first 'New Start Concurrency_1' then '3D point cloud scan and reference point correction';
        succession first 'New Start Concurrency_1' then 'Authentication and calibration of 19 units of equipment';
        succession first 'New End Concurrency_1' then done;
    }
    #Function
    action 'Level 4 autonomous construction and productivity maintenance' {
        #Function
        action 'Autonomous construction start' {
            in item 'Work routes and bypass routes' : ItemInputEdge;
        }
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
        action 'Remote control of unmanned equipment fleet';

        fork 'New Start Concurrency_2';
        join 'New End Concurrency_2';
        join 'New End Concurrency_3';

        attribute 'Visibility 200 m or less' : ScalarValues::Boolean;  // control: decision
        attribute 'Two or more units do not leave work at the same time' : ScalarValues::Boolean;  // control: scheduling_guard

        allocate 'Autonomous construction start' to 'AI_ICP';
        allocate 'Autonomous construction start' to 'Unmanned equipment fleet';
        allocate 'Battery pack replacement' to 'BSS_T';
        allocate 'Battery swap sequence optimization' to 'AI_ICP';
        allocate 'U-EDT Unit 7 hydraulic module preventive maintenance' to 'Site maintenance team';
        allocate 'OTA route optimization patch application' to 'Unmanned equipment fleet';
        allocate 'Remote control of unmanned equipment fleet' to 'Remote operator';

        succession first start then 'New Start Concurrency_2';
        succession first 'Autonomous construction start' if 'Visibility 200 m or less' == true then 'New End Concurrency_2';
        succession first 'Battery swap sequence optimization' if 'Two or more units do not leave work at the same time' == true then 'New End Concurrency_2';
        succession first 'Battery pack replacement' then 'New End Concurrency_3';
        succession first 'U-EDT Unit 7 hydraulic module preventive maintenance' then 'New End Concurrency_3';
        succession first 'OTA route optimization patch application' then 'New End Concurrency_3';
        succession first 'Remote control of unmanned equipment fleet' then 'New End Concurrency_3';
        succession first 'New Start Concurrency_2' then 'Autonomous construction start';
        succession first 'New Start Concurrency_2' then 'Battery swap sequence optimization';
        succession first 'New Start Concurrency_2' then 'U-EDT Unit 7 hydraulic module preventive maintenance';
        succession first 'New Start Concurrency_2' then 'OTA route optimization patch application';
        succession first 'New Start Concurrency_2' then 'Remote control of unmanned equipment fleet';
        succession first 'New End Concurrency_2' then 'Battery pack replacement';
        succession first 'New End Concurrency_3' then done;
    }
    #Function
    action 'Fog and cyber threat response' {
        #Function
        action 'Level 3 downgrade proposal and approval due to fog';
        #Function
        action 'External public network blocking and switch to internal security network' {
            out item 'Security threat log' : ItemOutputEdge;
        }

        fork 'New Start Concurrency_3';
        join 'New End Concurrency_4';

        allocate 'Level 3 downgrade proposal and approval due to fog' to 'AI_ICP';
        allocate 'Level 3 downgrade proposal and approval due to fog' to 'Remote supervisor';
        allocate 'External public network blocking and switch to internal security network' to 'Security system';

        succession first start then 'New Start Concurrency_3';
        succession first 'Level 3 downgrade proposal and approval due to fog' then 'New End Concurrency_4';
        succession first 'External public network blocking and switch to internal security network' then 'New End Concurrency_4';
        succession first 'New Start Concurrency_3' then 'Level 3 downgrade proposal and approval due to fog';
        succession first 'New Start Concurrency_3' then 'External public network blocking and switch to internal security network';
        succession first 'New End Concurrency_4' then done;
    }
    #Function
    action 'Heavy rain and work stop' {
        #Function
        action 'Forced work stop and safe evacuation';
        #Function
        action 'U-EEX Unit 2 pedestrian detection local stop';

        fork 'New Start Concurrency_4';
        join 'New End Concurrency_5';

        allocate 'Forced work stop and safe evacuation' to 'Remote supervisor';
        allocate 'Forced work stop and safe evacuation' to 'Unmanned equipment fleet';
        allocate 'U-EEX Unit 2 pedestrian detection local stop' to 'U-EEX Unit 2';

        succession first start then 'New Start Concurrency_4';
        succession first 'Forced work stop and safe evacuation' then 'New End Concurrency_5';
        succession first 'U-EEX Unit 2 pedestrian detection local stop' then 'New End Concurrency_5';
        succession first 'New Start Concurrency_4' then 'Forced work stop and safe evacuation';
        succession first 'New Start Concurrency_4' then 'U-EEX Unit 2 pedestrian detection local stop';
        succession first 'New End Concurrency_5' then done;
    }
    #Function
    action 'Recovery after heavy rain and mission completion' {
        #Function
        action 'Terrain rescan and reference point re-correction after heavy rain';
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

        fork 'New Start Concurrency_5';
        join 'New End Concurrency_6';

        attribute 'Heavy rain end confirmed' : ScalarValues::Boolean;  // control: guarded_sequence

        allocate 'Terrain rescan and reference point re-correction after heavy rain' to 'DMSS';
        allocate 'Terrain rescan and reference point re-correction after heavy rain' to 'ASPCS';
        allocate 'Subsidence zone bypass route recalculation' to 'AI_ICP';
        allocate 'Construction resumption and return to Level 4' to 'Remote supervisor';
        allocate 'Construction resumption and return to Level 4' to 'Unmanned equipment fleet';
        allocate 'Automatic generation of 72 h mission final report' to 'ICCC';
        allocate 'Automatic generation of 72 h mission final report' to 'AI_ICP';

        succession first start then 'New Start Concurrency_5';
        succession first 'Terrain rescan and reference point re-correction after heavy rain' if 'Heavy rain end confirmed' == true then 'Construction resumption and return to Level 4';
        succession first 'Subsidence zone bypass route recalculation' then 'New End Concurrency_6';
        succession first 'Construction resumption and return to Level 4' then 'New End Concurrency_6';
        succession first 'Automatic generation of 72 h mission final report' then 'New End Concurrency_6';
        succession first 'New Start Concurrency_5' then 'Terrain rescan and reference point re-correction after heavy rain';
        succession first 'New Start Concurrency_5' then 'Subsidence zone bypass route recalculation';
        succession first 'New Start Concurrency_5' then 'Automatic generation of 72 h mission final report';
        succession first 'New End Concurrency_6' then done;
    }

    item 'Battery pack';
    item '3D point cloud terrain data';
    item 'BIM and digital twin model';
    item 'Work routes and bypass routes';
    item 'Security threat log';
    item 'Comprehensive performance report';

    succession first start then 'Site setup and Level 3 start';
    succession first 'Site setup and Level 3 start' then 'Level 4 autonomous construction and productivity maintenance';
    succession first 'Level 4 autonomous construction and productivity maintenance' then 'Fog and cyber threat response';
    succession first 'Fog and cyber threat response' then 'Heavy rain and work stop';
    succession first 'Heavy rain and work stop' then 'Recovery after heavy rain and mission completion';
    succession first 'Recovery after heavy rain and mission completion' then done;
}
