private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// NGHE 72-hour autonomous construction
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
part 'U-EEX excavators' : Performer;
#Performer
part 'U-EDT dump trucks' : Performer;
#Performer
part 'U-EDB dozers' : Performer;
#Performer
part 'U-ERC rollers' : Performer;
#Performer
part 'BSS_T' : Performer;
#Performer
part 'DMSS' : Performer;
#Performer
part 'ASPCS' : Performer;
#Performer
part 'Security system' : Performer;
#Performer
part 'U-EEX 1' : Performer;
#Performer
part 'U-EEX 2' : Performer;
#Performer
part 'U-EEX 3' : Performer;
#Performer
part 'U-EDT 7' : Performer;

#Function
action 'NGHE 72-hour autonomous construction' {
    #Function
    action 'E1 Site setup and Level 3 start' {
        #Function
        action 'Install energy infrastructure, stock packs' {
            out item 'Battery pack' : ItemOutputEdge;
        }
        #Function
        action 'Verify RTDD latency and HSM auth';
        #Function
        action 'Scan 3D point cloud, correct datums' {
            out item '3D point-cloud terrain data' : ItemOutputEdge;
            out item 'BIM and digital-twin model' : ItemOutputEdge;
        }
        #Function
        action 'Authenticate and calibrate 19 machines';

        fork 'New Start Concurrency_1';
        join 'New End Concurrency_1';

        allocate 'Install energy infrastructure, stock packs' to 'Site maintenance team';
        allocate 'Verify RTDD latency and HSM auth' to 'Site supervisor';
        allocate 'Verify RTDD latency and HSM auth' to 'ICCC';
        allocate 'Scan 3D point cloud, correct datums' to 'DMSS';
        allocate 'Scan 3D point cloud, correct datums' to 'ASPCS';
        allocate 'Authenticate and calibrate 19 machines' to 'Unmanned equipment fleet';

        succession first start then 'New Start Concurrency_1';
        succession first 'Install energy infrastructure, stock packs' then 'New End Concurrency_1';
        succession first 'Verify RTDD latency and HSM auth' then 'New End Concurrency_1';
        succession first 'Scan 3D point cloud, correct datums' then 'New End Concurrency_1';
        succession first 'Authenticate and calibrate 19 machines' then 'New End Concurrency_1';
        succession first 'New Start Concurrency_1' then 'Install energy infrastructure, stock packs';
        succession first 'New Start Concurrency_1' then 'Verify RTDD latency and HSM auth';
        succession first 'New Start Concurrency_1' then 'Scan 3D point cloud, correct datums';
        succession first 'New Start Concurrency_1' then 'Authenticate and calibrate 19 machines';
        succession first 'New End Concurrency_1' then done;
    }
    #Function
    action 'E2 Level 4 autonomous production' {
        #Function
        action 'Start autonomous construction' {
            in item 'Work and detour routes' : ItemInputEdge;
        }
        #Function
        action 'Swap battery pack' {
            in item 'Battery pack' : ItemInputEdge;
        }
        #Function
        action 'Optimize battery-swap order';
        #Function
        action 'Preventive maintenance of U-EDT 7';
        #Function
        action 'Apply OTA route patch';
        #Function
        action 'Remotely monitor the unmanned fleet';

        fork 'New Start Concurrency_2';
        join 'New End Concurrency_2';
        join 'New End Concurrency_3';

        attribute 'visibility at most 200 m' : ScalarValues::Boolean;  // control: decision
        attribute 'never two machines out at once' : ScalarValues::Boolean;  // control: scheduling_guard

        allocate 'Start autonomous construction' to 'AI_ICP';
        allocate 'Start autonomous construction' to 'Unmanned equipment fleet';
        allocate 'Swap battery pack' to 'BSS_T';
        allocate 'Optimize battery-swap order' to 'AI_ICP';
        allocate 'Preventive maintenance of U-EDT 7' to 'Site maintenance team';
        allocate 'Apply OTA route patch' to 'Unmanned equipment fleet';
        allocate 'Remotely monitor the unmanned fleet' to 'Remote operator';

        succession first start then 'New Start Concurrency_2';
        succession first 'Start autonomous construction' if 'visibility at most 200 m' == true then 'New End Concurrency_2';
        succession first 'Optimize battery-swap order' if 'never two machines out at once' == true then 'New End Concurrency_2';
        succession first 'Swap battery pack' then 'New End Concurrency_3';
        succession first 'Preventive maintenance of U-EDT 7' then 'New End Concurrency_3';
        succession first 'Apply OTA route patch' then 'New End Concurrency_3';
        succession first 'Remotely monitor the unmanned fleet' then 'New End Concurrency_3';
        succession first 'New Start Concurrency_2' then 'Start autonomous construction';
        succession first 'New Start Concurrency_2' then 'Optimize battery-swap order';
        succession first 'New Start Concurrency_2' then 'Preventive maintenance of U-EDT 7';
        succession first 'New Start Concurrency_2' then 'Apply OTA route patch';
        succession first 'New Start Concurrency_2' then 'Remotely monitor the unmanned fleet';
        succession first 'New End Concurrency_2' then 'Swap battery pack';
        succession first 'New End Concurrency_3' then done;
    }
    #Function
    action 'E3 Fog and cyber threat response' {
        #Function
        action 'Propose and approve Level 3 in fog';
        #Function
        action 'Cut public network, switch to closed net' {
            out item 'Security threat log' : ItemOutputEdge;
        }

        fork 'New Start Concurrency_3';
        join 'New End Concurrency_4';

        allocate 'Propose and approve Level 3 in fog' to 'AI_ICP';
        allocate 'Propose and approve Level 3 in fog' to 'Remote supervisor';
        allocate 'Cut public network, switch to closed net' to 'Security system';

        succession first start then 'New Start Concurrency_3';
        succession first 'Propose and approve Level 3 in fog' then 'New End Concurrency_4';
        succession first 'Cut public network, switch to closed net' then 'New End Concurrency_4';
        succession first 'New Start Concurrency_3' then 'Propose and approve Level 3 in fog';
        succession first 'New Start Concurrency_3' then 'Cut public network, switch to closed net';
        succession first 'New End Concurrency_4' then done;
    }
    #Function
    action 'E4 Heavy rain and work stop' {
        #Function
        action 'Force work stop and evacuate';
        #Function
        action 'Local stop of U-EEX 2 on pedestrian';

        fork 'New Start Concurrency_4';
        join 'New End Concurrency_5';

        allocate 'Force work stop and evacuate' to 'Remote supervisor';
        allocate 'Force work stop and evacuate' to 'Unmanned equipment fleet';
        allocate 'Local stop of U-EEX 2 on pedestrian' to 'U-EEX 2';

        succession first start then 'New Start Concurrency_4';
        succession first 'Force work stop and evacuate' then 'New End Concurrency_5';
        succession first 'Local stop of U-EEX 2 on pedestrian' then 'New End Concurrency_5';
        succession first 'New Start Concurrency_4' then 'Force work stop and evacuate';
        succession first 'New Start Concurrency_4' then 'Local stop of U-EEX 2 on pedestrian';
        succession first 'New End Concurrency_5' then done;
    }
    #Function
    action 'E5 Recovery and mission completion' {
        #Function
        action 'Rescan terrain after rain';
        #Function
        action 'Recompute detour around subsidence' {
            out item 'Work and detour routes' : ItemOutputEdge;
        }
        #Function
        action 'Resume construction, return to Level 4';
        #Function
        action 'Generate 72-hour final report' {
            out item 'Final performance report' : ItemOutputEdge;
        }

        fork 'New Start Concurrency_5';
        join 'New End Concurrency_6';

        attribute 'end of rain confirmed' : ScalarValues::Boolean;  // control: guarded_sequence

        allocate 'Rescan terrain after rain' to 'DMSS';
        allocate 'Rescan terrain after rain' to 'ASPCS';
        allocate 'Recompute detour around subsidence' to 'AI_ICP';
        allocate 'Resume construction, return to Level 4' to 'Remote supervisor';
        allocate 'Resume construction, return to Level 4' to 'Unmanned equipment fleet';
        allocate 'Generate 72-hour final report' to 'ICCC';
        allocate 'Generate 72-hour final report' to 'AI_ICP';

        succession first start then 'New Start Concurrency_5';
        succession first 'Rescan terrain after rain' if 'end of rain confirmed' == true then 'Resume construction, return to Level 4';
        succession first 'Recompute detour around subsidence' then 'New End Concurrency_6';
        succession first 'Resume construction, return to Level 4' then 'New End Concurrency_6';
        succession first 'Generate 72-hour final report' then 'New End Concurrency_6';
        succession first 'New Start Concurrency_5' then 'Rescan terrain after rain';
        succession first 'New Start Concurrency_5' then 'Recompute detour around subsidence';
        succession first 'New Start Concurrency_5' then 'Generate 72-hour final report';
        succession first 'New End Concurrency_6' then done;
    }

    item 'Battery pack';
    item '3D point-cloud terrain data';
    item 'BIM and digital-twin model';
    item 'Work and detour routes';
    item 'Security threat log';
    item 'Final performance report';

    succession first start then 'E1 Site setup and Level 3 start';
    succession first 'E1 Site setup and Level 3 start' then 'E2 Level 4 autonomous production';
    succession first 'E2 Level 4 autonomous production' then 'E3 Fog and cyber threat response';
    succession first 'E3 Fog and cyber threat response' then 'E4 Heavy rain and work stop';
    succession first 'E4 Heavy rain and work stop' then 'E5 Recovery and mission completion';
    succession first 'E5 Recovery and mission completion' then done;
}
