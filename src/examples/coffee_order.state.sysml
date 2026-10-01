package 'Cafe order processing example' {
    private import ScalarValues::*;

    // Cafe order processing example
    // Generated from T2A-ESS by t2a_sysml.state.v0.1

    // events that trigger transitions (accept payloads)
    attribute def 'Payment approval';
    attribute def 'Order ticket receipt';
    attribute def 'Beverage completion';

    state def 'Coffee order scenario' {
        // guards (constrained_by on transitions)
        attribute 'Payment within 3 min' : Boolean;

        state 'order_status' {
            entry; then 'Order waiting state';

            // has_situation: Order taking
            state 'Order waiting state' {
                doc /* order_status = waiting; queue_length = 0 orders */
            }
            // has_situation: Order taking
            state 'Payment completed state' {
                doc /* order_status = paid */
            }
            // has_situation: Beverage preparation
            state 'Making state' {
                doc /* order_status = making */
            }
            // has_situation: Beverage preparation
            state 'Serving completed state' {
                doc /* order_status = served */
            }

            transition 'Transition from order waiting to payment completed'
                first 'Order waiting state'
                accept 'Payment approval'
                if 'Payment within 3 min'
                do action 'Payment'
                then 'Payment completed state';
            transition 'Transition from payment completed to making'
                first 'Payment completed state'
                accept 'Order ticket receipt'
                then 'Making state';
            transition 'Transition from making to serving completed'
                first 'Making state'
                accept 'Beverage completion'
                do action 'Serving'
                then 'Serving completed state';
        }
    }
}
