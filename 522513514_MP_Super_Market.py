# M.A. Asma 
# 522513514
# S22010125

import random 
import simpy
import statistics
import matplotlib.pyplot as plt
import csv  # new import for CSV

# The function to save combined scenario logs to CSV
def save_all_scenarios_csv(all_scenario_records, filename="supermarket_all_scenarios.csv"):
    fieldnames = ['CustomerID', 'ArrivalTime', 'LaneType', 'AssignedCashier', 'WaitTime', 'ServiceTime', 'DepartureTime', 'Scenario', 'Status']
    
    with open(filename, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for scenario_records in all_scenario_records:
            for record in scenario_records:
                writer.writerow(record)

# Supermarket simulation function
def supermarket_simulation(num_cashiers=4, sim_time=480, arrival_rate=0.4, service_mean=7.5, seed=42, verbose=True, scenario_name="Unnamed"):
    random.seed(seed)
    
    # tracking variables for metrics
    wait_times = []    # wait times of served customers   
    total_busy_time = 0.0  # total time cashiers are busy       
    customers_who_waited = 0    # count of customers who had to wait  
    queue_history = []   # track queue lengths over time         
    event_logs = []  # log of events for analysis             
    customer_records = []  # records for CSV        
    customers_left = 0    # track impatient customers who leave
    
    max_wait_time = 30  # customers leave if they wait more than 20 minutes

    # Define SimPy environment
    env = simpy.Environment()

    # Multiple queues: normal lane and express lane
    express_cashiers = simpy.Resource(env, capacity=max(1, num_cashiers // 3))  # smaller express lane
    normal_cashiers = simpy.Resource(env, capacity=num_cashiers - express_cashiers.capacity) 

    # Customer process
    def customer(env, cust_id):
        nonlocal total_busy_time, customers_who_waited, customers_left # track impatient customers who leave
        arrival_time = env.now  # customer arrival time

        # Decide lane (30% express, 70% normal)
        lane_type = "Express" if random.random() < 0.3 else "Normal"  # assign lane type
        cashier_resource = express_cashiers if lane_type == "Express" else normal_cashiers # select appropriate cashier resource

        log = f"Customer {cust_id} ({lane_type}) arrives at {arrival_time:.2f} minutes" # log arrival
        event_logs.append(log)  
        if verbose: print(log) 

        queue_history.append((env.now, len(normal_cashiers.queue) + len(express_cashiers.queue)))  # log queue length at arrival

        with cashier_resource.request() as req:
            # Wait with impatience condition (customer leaves if wait > max_wait_time)
            result = yield req | env.timeout(max_wait_time)
            if req not in result:
                # Customer leaves due to impatience
                leave_time = env.now  # time customer leaves
                customers_left += 1  # increment count of customers who left
                log = f"Customer {cust_id} ({lane_type}) left after waiting too long ({leave_time - arrival_time:.2f} min)"  # log leaving
                event_logs.append(log)  # append to event logs
                if verbose: print(log)  # print leaving log
                
                # Record as 'Left' in CSV
                customer_records.append({
                    'CustomerID': cust_id,  # customer ID
                    'ArrivalTime': round(arrival_time, 2),  # arrival time
                    'LaneType': lane_type,  # lane type
                    'AssignedCashier': 'N/A',  # no cashier assigned
                    'WaitTime': round(leave_time - arrival_time, 2),  # wait time before leaving
                    'ServiceTime': 0,  # no service time
                    'DepartureTime': round(leave_time, 2), # departure time
                    'Scenario': scenario_name,  # scenario name
                    'Status': 'Left'  # status as 'Left' 
                })
                return  # skip service since customer left

            # If served (didn't leave)
            start_service_time = env.now  # time service starts
            wait = start_service_time - arrival_time  # calculate wait time 
            wait_times.append(wait)  # record wait time 
            if wait > 0:  # increment count if customer waited
                customers_who_waited += 1  # increment count if customer waited 

            log = f"Customer {cust_id} ({lane_type}) assigned after waiting {wait:.2f} minutes at {start_service_time:.2f}" # log assignment
            event_logs.append(log) # append to event logs 
            if verbose: print(log) # print assignment log 

            queue_history.append((env.now, len(normal_cashiers.queue) + len(express_cashiers.queue)))

            service_time = random.expovariate(1.0 / service_mean) # determine service time
            total_busy_time += service_time # accumulate busy time
            yield env.timeout(service_time) # simulate service time

            depart_time = env.now  # time customer departs
            log = f"Customer {cust_id} ({lane_type}) departed at {depart_time:.2f} minutes (service {service_time:.2f} min)" # log departure
            event_logs.append(log) # append to event logs
            if verbose: print(log) # print departure log

            queue_history.append((env.now, len(normal_cashiers.queue) + len(express_cashiers.queue))) 

            # Record for CSV (Served)
            customer_records.append({
                'CustomerID': cust_id, # customer ID
                'ArrivalTime': round(arrival_time, 2), # arrival time
                'LaneType': lane_type, # lane type
                'AssignedCashier': len(cashier_resource.users), # assigned cashier number
                'WaitTime': round(wait, 2),  # wait time
                'ServiceTime': round(service_time, 2), # service time
                'DepartureTime': round(depart_time, 2),  # departure time
                'Scenario': scenario_name, # scenario name
                'Status': 'Served' # status as "Served"
            })

    # Arrival generator
    def arrival_generator(env):  # generate customer arrivals
        cust_id = 1  # customer ID counter
        while True:  
            inter_arrival = random.expovariate(arrival_rate)  # time until next arrival
            yield env.timeout(inter_arrival)  # wait for next arrival
            if env.now >= sim_time:  # stop arrivals if simulation time exceeded 
                break  # exit loop
            env.process(customer(env, cust_id)) # start customer process 
            cust_id += 1 # increment customer ID 

    env.process(arrival_generator(env))  # start arrival generator
    env.run(until=sim_time)  # run simulation

    total_served = len(wait_times)   # total customers served
    avg_wait = statistics.mean(wait_times) if wait_times else 0.0  # average wait time
    throughput = total_served / sim_time if sim_time > 0 else 0.0  # throughput calculation
    final_queue = len(normal_cashiers.queue) + len(express_cashiers.queue)  # final queue length 
    percent_waited = (customers_who_waited / total_served * 100.0) if total_served > 0 else 0.0  # percent who waited
    percent_immediate = 100.0 - percent_waited # percent served immediately
    utilization = min((total_busy_time / (num_cashiers * sim_time) * 100.0), 100.0)  # cashier utilization 
    
    print(f"\n=== {scenario_name} Results ===")  # print scenario results 
    print(f"Simulation complete (time: {sim_time} min).")  # print completion message 
    print(f"Total customers served: {total_served}") # print total served 
    print(f"Customers who left: {customers_left}") # print customers who left
    print(f"Average wait time: {avg_wait:.2f} min")  # print average wait time
    print(f"Throughput: {throughput:.3f} cust/min")  # print throughput
    print(f"Final queue length: {final_queue}")  # print final queue length
    print(f"Percent customers who waited: {percent_waited:.2f}%")  # print percent who waited
    print(f"Percent served immediately: {percent_immediate:.2f}%") # print percent served immediately
    print(f"Cashier utilization: {utilization:.2f}%") # print utilization

    return {
        'total_served': total_served, # total customers served
        'avg_wait': avg_wait,   # average wait time
        'throughput': throughput, # throughput
        'final_queue': final_queue, # final queue length
        'wait_times': wait_times, # list of wait times
        'queue_history': queue_history, # queue length history
        'percent_waited': percent_waited, # percent who waited
        'percent_immediate': percent_immediate, # percent served immediately
        'utilization': utilization, # cashier utilization
        'event_logs': event_logs, # event logs
        'num_cashiers': num_cashiers, # number of cashiers
        'sim_time': sim_time, # simulation time
        'arrival_rate': arrival_rate, # arrival rate
        'service_mean': service_mean, # average service time
        'customer_records': customer_records # records for CSV
    }

# Visualization function (unchanged)
def plot_visualizations(results_dict, scenario_name):
    plt.figure(figsize=(8, 5)) 
    plt.hist(results_dict['wait_times'], bins=10, edgecolor='black', alpha=0.7) 
    plt.xlabel('Wait Time (minutes)') 
    plt.ylabel('Frequency')
    plt.title(f'Wait Time Distribution - {scenario_name}')
    plt.savefig(f'wait_histogram_{scenario_name.lower().replace(" ", "_")}.png')
    plt.show()
    
    if results_dict['queue_history']: 
        times, queue_lens = zip(*results_dict['queue_history']) 
    else:
        times, queue_lens = ([0], [0]) 
    plt.figure(figsize=(10, 6))
    plt.step(times, queue_lens, where='post')  
    plt.scatter(times, queue_lens, s=10)
    plt.xlabel('Time (minutes)')
    plt.ylabel('Queue Length')
    plt.title(f'Queue Length Over Time - {scenario_name}')
    plt.grid(True)
    plt.savefig(f'queue_line_{scenario_name.lower().replace(" ", "_")}.png')
    plt.show()
    
    metrics = ['Avg Wait (min)', 'Throughput (cust/min)', 'Final Queue', '% Waited', 'Utilization %'] 
    values = [results_dict['avg_wait'], results_dict['throughput'], results_dict['final_queue'],
              results_dict['percent_waited'], results_dict['utilization']]
    plt.figure(figsize=(10, 5)) 
    bars = plt.bar(metrics, values)
    plt.title(f'Key Metrics - {scenario_name}')
    plt.ylabel('Value')
    plt.xticks(rotation=15)
    for bar in bars:
        h = bar.get_height()
        plt.annotate(f'{h:.2f}', xy=(bar.get_x() + bar.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
    plt.savefig(f'metrics_bar_{scenario_name.lower().replace(" ", "_")}.png')
    plt.show()

# Scenario runner (unchanged)
def run_experiments(base_params, verbose=True):  # run multiple scenarios
    scenarios = [
        ('Baseline', base_params),  # baseline scenario
        ('High Traffic', {**base_params, 'arrival_rate': base_params['arrival_rate'] * 2}),  # high traffic scenario
        ('More Cashiers', {**base_params, 'num_cashiers': max(1, base_params['num_cashiers'] * 2)}), # more cashiers scenario
        ('Faster Service', {**base_params, 'service_mean': max(0.1, base_params['service_mean'] * 0.7)}) # faster service scenario
    ]
    
    results_list = []  # store results for all scenarios
    scenario_names = [] # store scenario names
    all_customer_records = [] # store customer records for all scenarios
    
    for name, params in scenarios:
        print(f"\n--- Running {name} Scenario ---")
        results = supermarket_simulation(num_cashiers=params['num_cashiers'], # number of cashiers
                                        sim_time=params['sim_time'],  # simulation time
                                        arrival_rate=params['arrival_rate'],  # arrival rate
                                        service_mean=params['service_mean'], # average service time
                                        seed=params.get('seed', 42), # random seed
                                        verbose=verbose, # verbosity flag
                                        scenario_name=name) # scenario name
        results_list.append(results) # append results
        scenario_names.append(name) # append scenario name
        all_customer_records.append(results['customer_records']) # append customer records
    
    save_all_scenarios_csv(all_customer_records) # save all scenario records to CSV
    print("\nAll scenario logs saved to 'supermarket_all_scenarios.csv'") 
    
    print("\n--- Experiment Summary Table ---")  # print summary table
    print("Scenario\tAvg Wait (min)\tThroughput (cust/min)\tFinal Queue\t%Waited\tUtil(%)")  # table header
    for i, name in enumerate(scenario_names): 
        r = results_list[i] # get results
        print(f"{name}\t\t{r['avg_wait']:.2f}\t\t{r['throughput']:.3f}\t\t{r['final_queue']}\t\t{r['percent_waited']:.1f}\t{r['utilization']:.1f}") # print row
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5)) # comparison bar charts
    ax1.bar(scenario_names, [r['avg_wait'] for r in results_list], color=['blue', 'red', 'green', 'purple'])
    ax1.set_title('Average Wait Time by Scenario')
    ax1.set_ylabel('Minutes')
    ax1.tick_params(axis='x', rotation=45)
    ax2.bar(scenario_names, [r['throughput'] for r in results_list], color=['blue', 'red', 'green', 'purple'])
    ax2.set_title('Throughput by Scenario')
    ax2.set_ylabel('Customers/Min')
    ax2.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    plt.savefig('scenario_comparison.png')
    plt.show()
    
    plot_visualizations(results_list[0], scenario_names[0])
    return results_list

# Main entry point
if __name__ == "__main__":  # main function
    print("=== Supermarket Cashier Checkout Simulation ===")  
    print("==============================")
    print("Enter parameters for baseline scenario:") # prompt for user input
    num_cashiers = int(input("Number of cashiers (default 4): ") or 4) 
    sim_time = int(input("Simulation time in minutes (default 480): ") or 480)
    arrival_rate = float(input("Arrival rate (cust/min, default 0.4): ") or 0.4)
    service_mean = float(input("Average service time per customer (min, default 7.5): ") or 7.5)
    
    base_params = {
        'num_cashiers': num_cashiers, # number of cashiers
        'sim_time': sim_time, # simulation time
        'arrival_rate': arrival_rate, # arrival rate
        'service_mean': service_mean, # average service time
        'seed': 42 # random seed
    }
    
    results = run_experiments(base_params, verbose=True) # run experiments with user parameters
    
    print("\nApplication terminated!")
    print("=== Good Bye! ===") 
