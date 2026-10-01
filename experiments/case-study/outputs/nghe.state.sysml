package 'NGHE 72-hour autonomous construction' {
    private import ScalarValues::*;

    // NGHE 72-hour autonomous construction
    // Generated from T2A-ESS by t2a_sysml.state.v0.1

    // events that trigger transitions (accept payloads)
    attribute def 'Level 4 switch approved';
    attribute def 'Dense fog occurs';
    attribute def 'Forged command packet injected';
    attribute def 'Heavy rain sets in';
    attribute def 'End of rain confirmed';
    attribute def '72-hour mission completed';
    attribute def 'About 30 min of normal operation confirmed';

    state def 'NGHE 72-hour autonomous construction' parallel {
        // guards (constrained_by on transitions)
        attribute 'completed_volume >= 38000 m3 within 72 hours' : Boolean;
        attribute 'speed <= 5 km/h during fog degraded mode' : Boolean;

        state 'autonomy_level' {
            entry; then 'Level 3 supervised autonomy';

            // has_situation: E1 Site setup and Level 3 start
            state 'Level 3 supervised autonomy' {
                doc /* autonomy_level = Level 3 */
            }
            // has_situation: E2 Level 4 autonomous production
            state 'Level 4 full autonomy' {
                doc /* autonomy_level = Level 4 */
            }
            // has_situation: E4 Heavy rain and work stop
            state 'Level 1 emergency stop' {
                doc /* autonomy_level = Level 1; rainfall_rate = 30 mm/h */
            }
            // has_situation: E5 Recovery and mission completion
            state '72-hour mission complete' {
                doc /* target_volume = 38000 m3; actual_volume = 38200 m3; human_accident_count = 0 */
            }
            // has_situation: E3 Fog and cyber threat response
            state 'Level 3 limited operation in fog' {
                doc /* autonomy_level = Level 3; visibility = 200 m; speed_limit = 5 km/h */
            }

            transition 'Level 3 to Level 4'
                first 'Level 3 supervised autonomy'
                accept 'Level 4 switch approved'
                then 'Level 4 full autonomy';
            transition 'Level 4 to Level 3 in fog'
                first 'Level 4 full autonomy'
                accept 'Dense fog occurs'
                if 'speed <= 5 km/h during fog degraded mode'
                then 'Level 3 limited operation in fog';
            transition 'Level 3 (fog) to Level 1 stop'
                first 'Level 3 limited operation in fog'
                accept 'Heavy rain sets in'
                then 'Level 1 emergency stop';
            transition 'Resume at Level 3 after rain'
                first 'Level 1 emergency stop'
                accept 'End of rain confirmed'
                then 'Level 3 supervised autonomy';
            transition 'Level 3 to Level 4 after recovery'
                first 'Level 3 supervised autonomy'
                accept 'About 30 min of normal operation confirmed'
                then 'Level 4 full autonomy';
            transition 'Mission in progress to complete'
                first 'Level 4 full autonomy'
                accept '72-hour mission completed'
                if 'completed_volume >= 38000 m3 within 72 hours'
                then '72-hour mission complete';
        }

        state 'battery_soc' {
            entry; then 'Low-power battery swap';

            // has_situation: E2 Level 4 autonomous production
            state 'Low-power battery swap' {
                doc /* battery_soc = 15 percent */
            }
        }

        state 'network_mode' {
            entry; then 'Public network in use';

            // has_situation: E3 Fog and cyber threat response
            state 'Closed security network' {
                doc /* network_mode = closed_internal */
            }
            // has_situation: E3 Fog and cyber threat response
            state 'Public network in use' {
                doc /* network_mode = external_public */
            }

            transition 'Public to closed network'
                first 'Public network in use'
                accept 'Forged command packet injected'
                then 'Closed security network';
        }
    }
}
