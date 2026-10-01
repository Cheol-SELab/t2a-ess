package 'MUM-T attack operation under EW' {
    private import ScalarValues::*;

    // MUM-T attack operation under EW
    // Generated from T2A-ESS by t2a_sysml.state.v0.1

    // events that trigger transitions (accept payloads)
    attribute def 'Packet loss above threshold persists';
    attribute def 'Heartbeat loss persists';
    attribute def 'Link remains stable';
    attribute def 'Bandwidth recovered';
    attribute def 'Drone 1 battery depleted, lands';

    state def 'MUM-T attack operation under EW' parallel {
        // guards (constrained_by on transitions)
        attribute 'packet_loss_rate > threshold for configured_duration' : Boolean;
        attribute 'heartbeat_loss_duration >= configured_duration' : Boolean;
        attribute 'link_stable_duration >= configured_duration' : Boolean;

        state 'communication_mode' {
            entry; then 'Comms normal';

            // has_situation: E1 Preparation under normal comms
            state 'Comms normal' {
                doc /* communication_mode = normal; data_mode = video_stream */
            }
            // has_situation: E3 EW jamming and comms degradation
            state 'Comms limited' {
                doc /* communication_mode = limited; data_mode = track_summary */
            }
            // has_situation: E3 EW jamming and comms degradation
            state 'Comms disconnected' {
                doc /* communication_mode = disconnected */
            }

            transition 'Normal to limited'
                first 'Comms normal'
                accept 'Packet loss above threshold persists'
                if 'packet_loss_rate > threshold for configured_duration'
                then 'Comms limited';
            transition 'Limited to disconnected'
                first 'Comms limited'
                accept 'Heartbeat loss persists'
                if 'heartbeat_loss_duration >= configured_duration'
                then 'Comms disconnected';
            transition 'Disconnected to limited'
                first 'Comms disconnected'
                accept 'Link remains stable'
                if 'link_stable_duration >= configured_duration'
                then 'Comms limited';
            transition 'Limited to normal'
                first 'Comms limited'
                accept 'Bandwidth recovered'
                then 'Comms normal';
        }

        state 'combat_power' {
            entry; then 'Objective secured';

            // has_situation: E4 Comms recovery and attack resumption
            state 'Objective secured' {
                doc /* combat_power = maintained */
            }
        }

        state 'available_drone_count' {
            entry; then 'Three drones available';

            // has_situation: E1 Preparation under normal comms
            state 'Three drones available' {
                doc /* available_drone_count = 3 */
            }
            // has_situation: E4 Comms recovery and attack resumption
            state 'Two drones available' {
                doc /* available_drone_count = 2 */
            }

            transition 'Available drones reduced from three to two'
                first 'Three drones available'
                accept 'Drone 1 battery depleted, lands'
                then 'Two drones available';
        }
    }
}
