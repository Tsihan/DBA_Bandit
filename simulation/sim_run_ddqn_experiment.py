"""
Deep Reinforcement Learning (DDQN) Index Selection Runner for PostgreSQL
This script runs DDQN-based index selection experiments on PostgreSQL databases.
Uses PyTorch for better GPU support (RTX 5090).
"""

import pickle
from importlib import reload
import logging

import pandas as pd
from pandas import DataFrame

import constants
from bandits.experiment_report import ExpReport
from database.config_test_run import ConfigRunner
from shared import configs_v2 as configs, helper

print("=" * 80)
print("Using PyTorch DDQN Implementation")
print("=" * 80)


def add_total_time_row(df, total_workload_time):
    """Helper function to add total workload time row to DataFrame."""
    new_row = DataFrame([[-1, constants.MEASURE_TOTAL_WORKLOAD_TIME, total_workload_time]], 
                       columns=[constants.DF_COL_BATCH, constants.DF_COL_MEASURE_NAME, 
                               constants.DF_COL_MEASURE_VALUE])
    return pd.concat([df, new_row], ignore_index=True)


# Define Experiment ID list that we need to run
# You can modify this to use different experiment configurations
exp_id_list = ["job_benchmark_ddqn"]

# Comparing components - enable what you want to compare
DDQN = True  # Deep Q-Network (main component)
NO_INDEX = True  # Baseline without indexes
OPTIMAL = False  # Oracle optimal configuration (if available)
MAB = False  # Traditional MAB for comparison

# Generate from saved reports or run new experiments
FROM_FILE = False
SEPARATE_EXPERIMENTS = True
PLOT_LOG_Y = False
PLOT_MEASURE = (constants.MEASURE_BATCH_TIME, 
                constants.MEASURE_QUERY_EXECUTION_COST,
                constants.MEASURE_INDEX_CREATION_COST)

exp_report_list = []

for i in range(len(exp_id_list)):
    if SEPARATE_EXPERIMENTS:
        exp_report_list = []
    
    experiment_folder_path = helper.get_experiment_folder_path(exp_id_list[i])
    helper.change_experiment(exp_id_list[i])
    reload(configs)
    reload(logging)

    # Reload component flags from config
    DDQN = constants.COMPONENT_DDQN in configs.components
    NO_INDEX = constants.COMPONENT_NO_INDEX in configs.components
    OPTIMAL = constants.COMPONENT_OPTIMAL in configs.components
    MAB = constants.COMPONENT_MAB in configs.components

    # Configure logging
    if not FROM_FILE:
        logging.basicConfig(
            filename=experiment_folder_path + configs.experiment_id + '.log',
            filemode='w', 
            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.getLogger().setLevel(constants.LOGGING_LEVEL)

    if FROM_FILE:
        with open(experiment_folder_path + "reports.pickle", "rb") as f:
            exp_report_list = exp_report_list + pickle.load(f)
    else:
        print("=" * 80)
        print(f"Currently running DDQN experiment: {exp_id_list[i]}")
        print("=" * 80)
        
        # Running DDQN (Deep Q-Network)
        if DDQN:
            print("\n[DDQN] Starting Deep Reinforcement Learning Index Selection...")
            from simulation.sim_ddqn_v3 import Simulator as DDQNSimulator
            
            exp_report_ddqn = ExpReport(
                configs.experiment_id, 
                constants.COMPONENT_DDQN + exp_id_list[i],
                configs.reps, 
                configs.rounds
            )
            
            for r in range(configs.reps):
                print(f"  -> DDQN Repetition {r+1}/{configs.reps}")
                simulator = DDQNSimulator()
                results, total_workload_time = simulator.run()
                
                temp = DataFrame(results, 
                               columns=[constants.DF_COL_BATCH, 
                                       constants.DF_COL_MEASURE_NAME,
                                       constants.DF_COL_MEASURE_VALUE])
                temp = add_total_time_row(temp, total_workload_time)
                temp[constants.DF_COL_REP] = r
                exp_report_ddqn.add_data_list(temp)
                
                print(f"  -> DDQN Rep {r+1} completed. Total time: {total_workload_time:.2f}s")
            
            exp_report_list.append(exp_report_ddqn)
            print("[DDQN] Completed!\n")

        # Running No Index Baseline
        if NO_INDEX:
            print("\n[NO_INDEX] Running baseline without indexes...")
            exp_report_no_index = ExpReport(
                configs.experiment_id, 
                constants.COMPONENT_NO_INDEX + exp_id_list[i], 
                configs.reps,
                configs.rounds
            )
            
            for r in range(configs.reps):
                print(f"  -> NO_INDEX Repetition {r+1}/{configs.reps}")
                results, total_workload_time = ConfigRunner.run("no_index.sql", uniform=False)
                
                temp = DataFrame(results, 
                               columns=[constants.DF_COL_BATCH, 
                                       constants.DF_COL_MEASURE_NAME,
                                       constants.DF_COL_MEASURE_VALUE])
                temp = add_total_time_row(temp, total_workload_time)
                temp[constants.DF_COL_REP] = r
                exp_report_no_index.add_data_list(temp)
                
                print(f"  -> NO_INDEX Rep {r+1} completed. Total time: {total_workload_time:.2f}s")
            
            exp_report_list.append(exp_report_no_index)
            print("[NO_INDEX] Completed!\n")

        # Running Optimal Configuration
        if OPTIMAL:
            print("\n[OPTIMAL] Running oracle optimal configuration...")
            exp_report_optimal = ExpReport(
                configs.experiment_id, 
                constants.COMPONENT_OPTIMAL + exp_id_list[i], 
                configs.reps, 
                configs.rounds
            )
            
            for r in range(configs.reps):
                print(f"  -> OPTIMAL Repetition {r+1}/{configs.reps}")
                results, total_workload_time = ConfigRunner.run("optimal_config.sql", uniform=False)
                
                temp = DataFrame(results, 
                               columns=[constants.DF_COL_BATCH, 
                                       constants.DF_COL_MEASURE_NAME,
                                       constants.DF_COL_MEASURE_VALUE])
                temp = add_total_time_row(temp, total_workload_time)
                temp[constants.DF_COL_REP] = r
                exp_report_optimal.add_data_list(temp)
                
                print(f"  -> OPTIMAL Rep {r+1} completed. Total time: {total_workload_time:.2f}s")
            
            exp_report_list.append(exp_report_optimal)
            print("[OPTIMAL] Completed!\n")

        # Running MAB for Comparison
        if MAB:
            print("\n[MAB] Running traditional Multi-Armed Bandit for comparison...")
            Simulators = {}
            for mab_version in configs.mab_versions:
                Simulators[mab_version] = (getattr(__import__(mab_version, fromlist=['Simulator']), 'Simulator'))
            
            for version, Simulator in Simulators.items():
                version_number = version.split("_v", 1)[1]
                exp_report_mab = ExpReport(
                    configs.experiment_id,
                    constants.COMPONENT_MAB + version_number + exp_id_list[i], 
                    configs.reps,
                    configs.rounds
                )
                
                for r in range(configs.reps):
                    print(f"  -> MAB Repetition {r+1}/{configs.reps}")
                    simulator = Simulator()
                    results, total_workload_time = simulator.run()
                    
                    temp = DataFrame(results, 
                                   columns=[constants.DF_COL_BATCH, 
                                           constants.DF_COL_MEASURE_NAME,
                                           constants.DF_COL_MEASURE_VALUE])
                    temp = add_total_time_row(temp, total_workload_time)
                    temp[constants.DF_COL_REP] = r
                    exp_report_mab.add_data_list(temp)
                    
                    print(f"  -> MAB Rep {r+1} completed. Total time: {total_workload_time:.2f}s")
                
                exp_report_list.append(exp_report_mab)
            print("[MAB] Completed!\n")

        # Save results
        print("\n[SAVING] Saving experiment results...")
        with open(experiment_folder_path + "reports.pickle", "wb") as f:
            pickle.dump(exp_report_list, f)
        print("[SAVING] Results saved to reports.pickle\n")

        if SEPARATE_EXPERIMENTS:
            print("[PLOTTING] Generating plots and comparison tables...")
            helper.plot_exp_report(configs.experiment_id, exp_report_list, PLOT_MEASURE, PLOT_LOG_Y)
            helper.create_comparison_tables(configs.experiment_id, exp_report_list)
            print("[PLOTTING] Visualization completed!\n")

# Plot line graphs for combined experiments
if not SEPARATE_EXPERIMENTS:
    print("\n[PLOTTING] Generating combined plots and comparison tables...")
    helper.plot_exp_report(configs.experiment_id, exp_report_list, PLOT_MEASURE, PLOT_LOG_Y)
    helper.create_comparison_tables(configs.experiment_id, exp_report_list)
    print("[PLOTTING] All visualizations completed!\n")

print("=" * 80)
print("DDQN Experiment Completed Successfully!")
print("=" * 80)
