private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// MUM-T attack maneuver unstructured test text T2A-ESS exhaustive extraction result
// Generated from T2A-ESS by t2a_sysml.effbd.v0.3

#Performer
part 'Tank company' : Performer;
#Performer
part 'Company commander' : Performer;
#Performer
part 'TDSS' : Performer;
#Performer
part 'HMI' : Performer;
#Performer
part 'Three reconnaissance drones' : Performer;
#Performer
part 'Drone 1' : Performer;
#Performer
part 'Drone 2' : Performer;
#Performer
part 'Drone 3' : Performer;
#Performer
part 'Subordinate platoons' : Performer;
#Performer
part '1st Platoon' : Performer;
#Performer
part '2nd Platoon' : Performer;
#Performer
part '3rd Platoon' : Performer;
#Performer
part 'Battalion server' : Performer;
#Performer
part 'Enemy' : Performer;

#Function
action 'MUM-T attack maneuver and electronic warfare response full scenario' {
    #Function
    action 'MUM-T system activation';
    #Function
    action 'Fuse drone ISR and tank sensor cues' {
        out item 'Integrated SA' : ItemOutputEdge;
    }
    #Function
    action 'Perform TDSS self-diagnosis';
    #Function
    action 'Battalion server communication confirmed normal';
    #Function
    action 'Deploy drone surveillance zones';
    #Function
    action 'Sequential reconnaissance drone launch';
    #Function
    action 'HMI integrated SA display';
    #Function
    action 'Share drone surveillance status and expected enemy positions';
    #Function
    action 'Initial transmission of company SA summary information' {
        in item 'Company SA summary information' : ItemInputEdge;
    }
    #Function
    action 'Wedge formation lead maneuver';
    #Function
    action 'Forward and left and right flank surveillance';
    #Function
    action 'Update threat priorities';
    #Function
    action 'Detect suspected enemy observation post heat source';
    #Function
    action 'Enemy observation post possibility alert';
    #Function
    action 'Decide right bypass maneuver';
    #Function
    action 'Link target information to the battalion';
    #Function
    action 'Redeploy Drone 3 ahead of the bypass axis';
    #Function
    action 'Report progress when passing the control point';
    #Function
    action 'Multiple FPV drones detected';
    #Function
    action 'Display FPV threat direction, speed, ETA' {
        out item 'FPV threat alert' : ItemOutputEdge;
    }
    #Function
    action 'Order dispersed maneuver and air-defense watch';
    #Function
    action 'Urgent sharing of FPV threat information';
    #Function
    action 'Electronic warfare jamming begins';
    #Function
    action 'Start limited communication mode transition';
    #Function
    action 'Command to stop video transmission and switch to Edge AI mode';
    #Function
    action 'Transmit summary track data' {
        out item 'Summary track data' : ItemOutputEdge;
    }
    #Function
    action 'Update minimum SA';
    #Function
    action '1st Platoon Tank 3 FPV evasive maneuver';
    #Function
    action '2nd Platoon air-defense watch and dispersed maneuver';
    #Function
    action 'Order company assembly and damage check';
    #Function
    action 'Declare communication blackout mode transition';
    #Function
    action 'Logically block external information exchange';
    #Function
    action 'Activate local sensor-based survival loop';
    #Function
    action 'Drone switch to emergency broadcast mode';
    #Function
    action 'Direct broadcast of threat detection data' {
        out item 'Emergency broadcast threat data' : ItemOutputEdge;
    }
    #Function
    action 'Perform individual survival actions';
    #Function
    action 'Drone 2 FPV broadcast alert';
    #Function
    action '3rd Platoon evasive maneuver';
    #Function
    action 'Drone 3 ATGM alert broadcast';
    #Function
    action '2nd Platoon smoke screen deployment and evasive maneuver';
    #Function
    action 'Maintain minimum SA';
    #Function
    action 'Drone 1 battery depletion landing';
    #Function
    action 'Begin transition from blackout to limited mode';
    #Function
    action 'SA resynchronization';
    #Function
    action 'Attempt surveillance area reallocation';
    #Function
    action 'Transition from limited to normal communication mode';
    #Function
    action 'Resume SA sharing, target information linking, and battalion analysis reception';
    #Function
    action 'Comprehensive report on the blackout period';
    #Function
    action 'Reactivate operational activity groups';
    #Function
    action 'Decide on reduced surveillance toward the objective based on 2 drones';
    #Function
    action 'Order maneuver resumption';
    #Function
    action 'Remaining enemy force confirmed';
    #Function
    action 'Suppress remaining enemy positions';
    #Function
    action 'Organize defensive positions';
    #Function
    action 'Report objective secured';

    fork 'New Start Concurrency_1';
    join 'New End Concurrency_1';

    attribute 'Packet loss rate persistently exceeds the threshold' : ScalarValues::Boolean;  // control: decision
    attribute 'While the communication blackout state persists' : ScalarValues::Boolean;  // control: loop


    succession first start then 'New Start Concurrency_1';
    succession first 'Display FPV threat direction, speed, ETA' then 'Order dispersed maneuver and air-defense watch';
    succession first 'Electronic warfare jamming begins' if 'Packet loss rate persistently exceeds the threshold' == true then 'Command to stop video transmission and switch to Edge AI mode';
    succession first 'Declare communication blackout mode transition' then 'Activate local sensor-based survival loop';
    succession first 'Drone switch to emergency broadcast mode' if 'While the communication blackout state persists' == true then 'Perform individual survival actions';
    succession first 'MUM-T system activation' then 'New End Concurrency_1';
    succession first 'Fuse drone ISR and tank sensor cues' then 'New End Concurrency_1';
    succession first 'Perform TDSS self-diagnosis' then 'New End Concurrency_1';
    succession first 'Battalion server communication confirmed normal' then 'New End Concurrency_1';
    succession first 'Deploy drone surveillance zones' then 'New End Concurrency_1';
    succession first 'Sequential reconnaissance drone launch' then 'New End Concurrency_1';
    succession first 'HMI integrated SA display' then 'New End Concurrency_1';
    succession first 'Share drone surveillance status and expected enemy positions' then 'New End Concurrency_1';
    succession first 'Initial transmission of company SA summary information' then 'New End Concurrency_1';
    succession first 'Wedge formation lead maneuver' then 'New End Concurrency_1';
    succession first 'Forward and left and right flank surveillance' then 'New End Concurrency_1';
    succession first 'Update threat priorities' then 'New End Concurrency_1';
    succession first 'Detect suspected enemy observation post heat source' then 'New End Concurrency_1';
    succession first 'Enemy observation post possibility alert' then 'New End Concurrency_1';
    succession first 'Decide right bypass maneuver' then 'New End Concurrency_1';
    succession first 'Link target information to the battalion' then 'New End Concurrency_1';
    succession first 'Redeploy Drone 3 ahead of the bypass axis' then 'New End Concurrency_1';
    succession first 'Report progress when passing the control point' then 'New End Concurrency_1';
    succession first 'Multiple FPV drones detected' then 'New End Concurrency_1';
    succession first 'Order dispersed maneuver and air-defense watch' then 'New End Concurrency_1';
    succession first 'Urgent sharing of FPV threat information' then 'New End Concurrency_1';
    succession first 'Start limited communication mode transition' then 'New End Concurrency_1';
    succession first 'Command to stop video transmission and switch to Edge AI mode' then 'New End Concurrency_1';
    succession first 'Transmit summary track data' then 'New End Concurrency_1';
    succession first 'Update minimum SA' then 'New End Concurrency_1';
    succession first '1st Platoon Tank 3 FPV evasive maneuver' then 'New End Concurrency_1';
    succession first '2nd Platoon air-defense watch and dispersed maneuver' then 'New End Concurrency_1';
    succession first 'Order company assembly and damage check' then 'New End Concurrency_1';
    succession first 'Logically block external information exchange' then 'New End Concurrency_1';
    succession first 'Activate local sensor-based survival loop' then 'New End Concurrency_1';
    succession first 'Direct broadcast of threat detection data' then 'New End Concurrency_1';
    succession first 'Perform individual survival actions' then 'New End Concurrency_1';
    succession first 'Drone 2 FPV broadcast alert' then 'New End Concurrency_1';
    succession first '3rd Platoon evasive maneuver' then 'New End Concurrency_1';
    succession first 'Drone 3 ATGM alert broadcast' then 'New End Concurrency_1';
    succession first '2nd Platoon smoke screen deployment and evasive maneuver' then 'New End Concurrency_1';
    succession first 'Maintain minimum SA' then 'New End Concurrency_1';
    succession first 'Drone 1 battery depletion landing' then 'New End Concurrency_1';
    succession first 'Begin transition from blackout to limited mode' then 'New End Concurrency_1';
    succession first 'SA resynchronization' then 'New End Concurrency_1';
    succession first 'Attempt surveillance area reallocation' then 'New End Concurrency_1';
    succession first 'Transition from limited to normal communication mode' then 'New End Concurrency_1';
    succession first 'Resume SA sharing, target information linking, and battalion analysis reception' then 'New End Concurrency_1';
    succession first 'Comprehensive report on the blackout period' then 'New End Concurrency_1';
    succession first 'Reactivate operational activity groups' then 'New End Concurrency_1';
    succession first 'Decide on reduced surveillance toward the objective based on 2 drones' then 'New End Concurrency_1';
    succession first 'Order maneuver resumption' then 'New End Concurrency_1';
    succession first 'Remaining enemy force confirmed' then 'New End Concurrency_1';
    succession first 'Suppress remaining enemy positions' then 'New End Concurrency_1';
    succession first 'Organize defensive positions' then 'New End Concurrency_1';
    succession first 'Report objective secured' then 'New End Concurrency_1';
    succession first 'New Start Concurrency_1' then 'MUM-T system activation';
    succession first 'New Start Concurrency_1' then 'Fuse drone ISR and tank sensor cues';
    succession first 'New Start Concurrency_1' then 'Perform TDSS self-diagnosis';
    succession first 'New Start Concurrency_1' then 'Battalion server communication confirmed normal';
    succession first 'New Start Concurrency_1' then 'Deploy drone surveillance zones';
    succession first 'New Start Concurrency_1' then 'Sequential reconnaissance drone launch';
    succession first 'New Start Concurrency_1' then 'HMI integrated SA display';
    succession first 'New Start Concurrency_1' then 'Share drone surveillance status and expected enemy positions';
    succession first 'New Start Concurrency_1' then 'Initial transmission of company SA summary information';
    succession first 'New Start Concurrency_1' then 'Wedge formation lead maneuver';
    succession first 'New Start Concurrency_1' then 'Forward and left and right flank surveillance';
    succession first 'New Start Concurrency_1' then 'Update threat priorities';
    succession first 'New Start Concurrency_1' then 'Detect suspected enemy observation post heat source';
    succession first 'New Start Concurrency_1' then 'Enemy observation post possibility alert';
    succession first 'New Start Concurrency_1' then 'Decide right bypass maneuver';
    succession first 'New Start Concurrency_1' then 'Link target information to the battalion';
    succession first 'New Start Concurrency_1' then 'Redeploy Drone 3 ahead of the bypass axis';
    succession first 'New Start Concurrency_1' then 'Report progress when passing the control point';
    succession first 'New Start Concurrency_1' then 'Multiple FPV drones detected';
    succession first 'New Start Concurrency_1' then 'Display FPV threat direction, speed, ETA';
    succession first 'New Start Concurrency_1' then 'Urgent sharing of FPV threat information';
    succession first 'New Start Concurrency_1' then 'Electronic warfare jamming begins';
    succession first 'New Start Concurrency_1' then 'Start limited communication mode transition';
    succession first 'New Start Concurrency_1' then 'Transmit summary track data';
    succession first 'New Start Concurrency_1' then 'Update minimum SA';
    succession first 'New Start Concurrency_1' then '1st Platoon Tank 3 FPV evasive maneuver';
    succession first 'New Start Concurrency_1' then '2nd Platoon air-defense watch and dispersed maneuver';
    succession first 'New Start Concurrency_1' then 'Order company assembly and damage check';
    succession first 'New Start Concurrency_1' then 'Declare communication blackout mode transition';
    succession first 'New Start Concurrency_1' then 'Logically block external information exchange';
    succession first 'New Start Concurrency_1' then 'Drone switch to emergency broadcast mode';
    succession first 'New Start Concurrency_1' then 'Direct broadcast of threat detection data';
    succession first 'New Start Concurrency_1' then 'Drone 2 FPV broadcast alert';
    succession first 'New Start Concurrency_1' then '3rd Platoon evasive maneuver';
    succession first 'New Start Concurrency_1' then 'Drone 3 ATGM alert broadcast';
    succession first 'New Start Concurrency_1' then '2nd Platoon smoke screen deployment and evasive maneuver';
    succession first 'New Start Concurrency_1' then 'Maintain minimum SA';
    succession first 'New Start Concurrency_1' then 'Drone 1 battery depletion landing';
    succession first 'New Start Concurrency_1' then 'Begin transition from blackout to limited mode';
    succession first 'New Start Concurrency_1' then 'SA resynchronization';
    succession first 'New Start Concurrency_1' then 'Attempt surveillance area reallocation';
    succession first 'New Start Concurrency_1' then 'Transition from limited to normal communication mode';
    succession first 'New Start Concurrency_1' then 'Resume SA sharing, target information linking, and battalion analysis reception';
    succession first 'New Start Concurrency_1' then 'Comprehensive report on the blackout period';
    succession first 'New Start Concurrency_1' then 'Reactivate operational activity groups';
    succession first 'New Start Concurrency_1' then 'Decide on reduced surveillance toward the objective based on 2 drones';
    succession first 'New Start Concurrency_1' then 'Order maneuver resumption';
    succession first 'New Start Concurrency_1' then 'Remaining enemy force confirmed';
    succession first 'New Start Concurrency_1' then 'Suppress remaining enemy positions';
    succession first 'New Start Concurrency_1' then 'Organize defensive positions';
    succession first 'New Start Concurrency_1' then 'Report objective secured';
    succession first 'New End Concurrency_1' then done;

    item 'Integrated SA';
    item 'Company SA summary information';
    item 'FPV threat alert';
    item 'Summary track data';
    item 'Emergency broadcast threat data';
}
