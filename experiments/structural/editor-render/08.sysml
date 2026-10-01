private import IMMBaseSchema::*;
private import ScalarValues::*;

// self-contained EFFBD edge/performer definitions (editor-injected set)
item def ItemInputEdge;
item def ItemOutputEdge;
item def TriggeringItemInputEdge;
part def Performer;


// Cafe order processing example
// Generated from T2A-ESS by t2a_sysml.effbd.v0.3

#Performer
part 'Customer' : Performer;
#Performer
part 'Clerk' : Performer;
#Performer
part 'Barista' : Performer;

#Function
action 'Coffee order scenario' {
    #Function
    action 'Order taking' {
        #Function
        action 'Order entry' {
            out item 'Order ticket' : ItemOutputEdge;
        }
        #Function
        action 'Payment';

        attribute 'Payment completed' : ScalarValues::Boolean;  // control: decision

        allocate 'Order entry' to 'Customer';
        allocate 'Payment' to 'Clerk';

        succession first start then 'Order entry';
        succession first 'Order entry' if 'Payment completed' == true then 'Payment';
        succession first 'Payment' then done;
    }
    #Function
    action 'Beverage preparation' {
        #Function
        action 'Beverage making' {
            in item 'Order ticket' : ItemInputEdge;
        }
        #Function
        action 'Cup preheating';
        #Function
        action 'Serving';

        fork 'New Start Concurrency_1';
        join 'New End Concurrency_1';

        allocate 'Beverage making' to 'Barista';
        allocate 'Cup preheating' to 'Barista';
        allocate 'Serving' to 'Barista';

        succession first start then 'New Start Concurrency_1';
        succession first 'Beverage making' then 'New End Concurrency_1';
        succession first 'Cup preheating' then 'New End Concurrency_1';
        succession first 'Serving' then done;
        succession first 'New Start Concurrency_1' then 'Beverage making';
        succession first 'New Start Concurrency_1' then 'Cup preheating';
        succession first 'New End Concurrency_1' then 'Serving';
    }

    item 'Order ticket';

    succession first start then 'Order taking';
    succession first 'Order taking' then 'Beverage preparation';
    succession first 'Beverage preparation' then done;

    flow from 'Order taking'.'Order entry'.'Order ticket' to 'Beverage preparation'.'Beverage making'.'Order ticket';
}
