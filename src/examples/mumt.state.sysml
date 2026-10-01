package 'MUM-T attack maneuver ground truth (relation closure) scenario' {
    private import ScalarValues::*;

    // MUM-T attack maneuver ground truth (relation closure) scenario
    // Generated from T2A-ESS by t2a_sysml.state.v0.1

    // events that trigger transitions (accept payloads)
    attribute def 'Packet loss rate persistently exceeds the threshold';
    attribute def 'Persistent heartbeat loss';
    attribute def 'Link kept stable';
    attribute def 'Bandwidth recovery';
    attribute def 'Drone 1 battery depletion and landing';

    state def 'MUM-T-based attack maneuver and electronic warfare response' parallel {
        // guards (constrained_by on transitions)
        attribute 'Condition: packet loss rate persistently exceeds the threshold' : Boolean;
        attribute 'Condition: persistent heartbeat loss' : Boolean;
        attribute 'Condition: link kept stable' : Boolean;

        state 'communication_mode' {
            entry; then 'Normal communication state';

            // has_situation: Preparation and normal communication maneuver
            state 'Normal communication state' {
                doc /* communication_mode = normal; data_mode = video_stream */
            }
            // has_situation: Electronic warfare jamming and communication degradation response
            state 'Limited communication state' {
                doc /* communication_mode = limited; data_mode = track_summary */
            }
            // has_situation: Electronic warfare jamming and communication degradation response
            state 'Communication blackout state' {
                doc /* communication_mode = disconnected */
            }

            transition 'Transition from normal communication to limited communication'
                first 'Normal communication state'
                accept 'Packet loss rate persistently exceeds the threshold'
                if 'Condition: packet loss rate persistently exceeds the threshold'
                then 'Limited communication state';
            transition 'Transition from limited communication to communication blackout'
                first 'Limited communication state'
                accept 'Persistent heartbeat loss'
                if 'Condition: persistent heartbeat loss'
                then 'Communication blackout state';
            transition 'Transition from communication blackout to limited communication'
                first 'Communication blackout state'
                accept 'Link kept stable'
                if 'Condition: link kept stable'
                then 'Limited communication state';
            transition 'Transition from limited communication to normal communication'
                first 'Limited communication state'
                accept 'Bandwidth recovery'
                then 'Normal communication state';
        }

        state 'combat_power' {
            entry; then 'Objective secured state';

            // has_situation: Communication recovery and attack resumption
            state 'Objective secured state' {
                doc /* combat_power = maintained */
            }
        }

        state 'available_drone_count' {
            entry; then '3 drones operable state';

            // has_situation: Preparation and normal communication maneuver
            state '3 drones operable state' {
                doc /* available_drone_count = 3 */
            }
            // has_situation: Communication recovery and attack resumption
            state '2 drones operable state' {
                doc /* available_drone_count = 2 */
            }

            transition 'Available drones decrease from 3 to 2'
                first '3 drones operable state'
                accept 'Drone 1 battery depletion and landing'
                then '2 drones operable state';
        }
    }
}
