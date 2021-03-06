/*
 * cost_functions.h
 *  Class responsible for calculating cost for given trajectory, based on predictions and ego
 *  vehicle state.
 *
 *  Created on: Aug 10, 2017
 *      Author: ramiz
 */

#ifndef COST_FUNCTIONS_H_
#define COST_FUNCTIONS_H_

#include <cmath>
#include <map>
#include <iterator>
#include "vehicle.h"
#include "snapshot.h"
#include "trajectory_data.h"

using namespace std;

class CostFunctions {

public:
  CostFunctions();
  virtual ~CostFunctions();

  /**
   * @param vehicle, Ego vehicle for which to calculate cost of trajectory
   * @param predictions,  predicted trajectories of other nearby vehicles on road
   * @param trajectory,   trajectory for which to calculate cost of
   */
  double calculate_cost(const Vehicle &vehicle,
                        const map<int, vector<vector<int> > > &predictios,
                        const vector<Snapshot> &trajectory);

  /**
   * Calculates cost for changing lane based on trajectory data and predictions
   */
  double change_lane_cost(const Vehicle &vehicle,
                         const map<int, vector<vector<int> > > &predictions,
                         const vector<Snapshot> &trajectory,
                         const TrajectoryData &data);

  /**
   * Calculates cost for how far we are from goal lane and based on
   * in howmany timesteps we will reach to goal position.
   */
  double distance_from_goal_lane_cost(const Vehicle &vehicle,
                                      const map<int, vector<vector<int> > > &predictions,
                                      const vector<Snapshot> &trajectory,
                                      const TrajectoryData &data);

  /**
   * Calculates cost based on how far vehicle's velocity is from target velocity
   */
  double inefficiency_cost(const Vehicle &vehicle,
                           const map<int, vector<vector<int> > > &predictions,
                           const vector<Snapshot> &trajectory,
                           const TrajectoryData &data);

  /**
   * Calculates cost based on whether collision is detected or not
   */
  double collision_cost(const Vehicle &vehicle,
                        const map<int, vector<vector<int> > > &predictions,
                        const vector<Snapshot> &trajectory,
                        const TrajectoryData &data);

  /**
   * Calculates cost based on how much buffer we have from other traffic
   */
  double buffer_cost(const Vehicle &vehicle,
                     const map<int, vector<vector<int> > > &predictions,
                     const vector<Snapshot> &trajectory,
                     const TrajectoryData &data);

  /*
   * Constants
   */

  //time horizon based on which we want to decide
  //cost of trajectory
  const int PLANNING_HORIZON = 2;
  //timesteps buffer, vehicles should be these many timesteps away
  const double BUFFER_TIME = 1.5;

  //weights for each category of cost functions
  //Safety:
  const double COLLISION;
  const double DANGER;
  //Reach goal
  const double REACH_GOAL;
  //COMFORT
  const double COMFORT;
  //Efficiency
  const double EFFICIENCY;

  typedef double (CostFunctions::* cost_function_ptr)(const Vehicle &,
      const map<int, vector<vector<int> > > &,
      const vector<Snapshot> &,
      const TrajectoryData &);

  vector<cost_function_ptr> cost_functions_pointers;

private:
  /**
   * Calculates helper data needed for calculating cost functions
   */
  TrajectoryData calculate_helper_data(const Vehicle &vehicle,
                                       const map<int, vector<vector<int> > > &predictios,
                                       const vector<Snapshot> &trajectory);

  /**
   * Filter predictions and only keep predictions whose first prediction is in given lane
   */
  map<int, vector<vector<int> > > filter_predictions_by_lane(const map<int, vector<vector<int> > > &predictions, int lane);

  /**
   * Detects if there is a collision between two vehicles based on (s, v)
   */
  bool check_collision(const Snapshot& snapshot, int other_vehicle_s_now, int other_vehicle_s_previous);
};

#endif /* COST_FUNCTIONS_H_ */
