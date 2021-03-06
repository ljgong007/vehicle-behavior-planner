from my_cost_functions import calculate_cost
from collections import namedtuple
from copy import deepcopy
import pdb

Snapshot = namedtuple("Snapshot", ["lane", "s", "v", "a", "state"])

class Vehicle(object):
  L = 1
  preferred_buffer = 6 # impacts "keep lane" behavior.

  def __init__(self, lane, s, v, a):
    self.lane = lane
    self.s = s
    self.v = v
    self.a = a
    self.state = "CS"

    # The following are set when configure() is called.
    # All of them are integers.
    self.max_acceleration = None
    self.target_speed = None
    self.lanes_available = None
    self.goal_lane = None
    self.goal_s = None


  def update_state(self, predictions):
    """
    Updates the "state" of the vehicle by assigning one of the
    following values to 'self.state':

    "KL" - Keep Lane
     - The vehicle will attempt to drive its target speed, unless there is
       traffic in front of it, in which case it will slow down.

    "LCL" or "LCR" - Lane Change Left / Right
     - The vehicle will IMMEDIATELY change lanes and then follow longitudinal
       behavior for the "KL" state in the new lane.

    "PLCL" or "PLCR" - Prepare for Lane Change Left / Right
     - The vehicle will find the nearest vehicle in the adjacent lane which is
       BEHIND itself and will adjust speed to try to get behind that vehicle.

    INPUTS
    - predictions
    A dictionary. The keys are ids of other vehicles and the values are arrays
    where each entry corresponds to the vehicle's predicted location at the
    corresponding timestep. The FIRST element in the array gives the vehicle's
    current position. Example (showing a car with id 3 moving at 2 m/s):

    {
      3 : [
        {"s" : 4, "lane": 0},
        {"s" : 6, "lane": 0},
        {"s" : 8, "lane": 0},
        {"s" : 10, "lane": 0},
      ]
    }

    """
    state = self.get_next_state(predictions)
    self.state = state
    # self.state = "KL" # this is an example of how you change state.

  """
  Predicts next state by go through each state using Finite State Machine (FSM) alogrithm
  to choose the best next possible next.
  """
  def get_next_state(self, predictions):
      states = ["KL", "LCL", "LCR"]

      #let's remove impossible next states
      if self.lane == 0:
          #ego vehicle is at left most lane so LCL is not possible
          states.remove("LCL")
      elif self.lane == (self.lanes_available - 1):
          #ego vehicle is at right most lane so LCR is not possible
          states.remove("LCR")

      #let's calculate cost for each state
      costs = []
      for state in states:
          #make a copy of predictions as find_trajectory_for_state changes
          #predictions
          predictions_copy = deepcopy(predictions)
          #find trajectory to go take this state
          trajectory = self.find_trajectory_for_state(state, predictions_copy)

          #calculate cost for this trajectory
          cost = calculate_cost(self, trajectory, predictions)

          costs.append({"state": state, "cost": cost})

      #find (state, cost) pair with minimum cost
      best = min(costs, key=lambda s: s["cost"])
      return best["state"]

  """
  finds trajectory (sequence of behavior (lane, s, v, a, state) changes for given time horizon)
  for passed @param state and based on first 5 other vehicle predictions,
  for given time horizon (by default, horizon=5)
  and based on passed predictions
  """
  def find_trajectory_for_state(self, state, predictions, horizon=5):
      #save current state snapshot
      current_state_snapshot = self.take_snapshot()

      #pretend to be in given state
      self.state = state

      #a trajectory is a sequence of vehicle state snapshots
      #start defining trajectory by adding the current state
      #as starting point
      trajectory = [current_state_snapshot]

      for i in range(horizon):
          #reset vehicle state to original state
          self.restore_state_from_snapshot(current_state_snapshot)

          #pretend vehicle to be in passed state
          self.state = state
          #realize/apply this new state vehicle is in by
          #updating (a, lane)
          self.realize_state(predictions)

          #validate lane number and crash if invalid
          assert 0 <= self.lane < self.lanes_available, "Invalid lane {}".format(self.lane)

          #increment vehicle (s, v) for 1 timestep
          self.increment()

          #append this new vehicle state snapshot to trajectory
          trajectory.append(self.take_snapshot())

          #remove predictions of other vehicle for current timehorizon
          #which is: Remove first prediction of each vehicle
          for v_id, v in predictions.items():
              v.pop(0)

              #now that trajectory is found we need to reset
              #this vehicle's state to its original state
              self.restore_state_from_snapshot(current_state_snapshot)

              return trajectory

  """
  Saves current vehicle state into a Snapshot
  """
  def take_snapshot(self):
      return Snapshot(self.lane, self.s, self.v, self.a, self.state)

  """
  Restores vehicle state (lane, s, v, a, state) from given snapshot
  """
  def restore_state_from_snapshot(self, snapshot):
      self.lane = snapshot.lane
      self.s = snapshot.s
      self.v = snapshot.v
      self.a = snapshot.a
      self.state = snapshot.state

  """
  Called by simulator before simulation begins. Sets various
  parameters (target_speed, lanes_available, max_acceleration, goal_lane, goal_s)
  which will impact the ego vehicle.
  """
  def configure(self, road_data):
    """
    Called by simulator before simulation begins. Sets various
    parameters which will impact the ego vehicle.
    """
    self.target_speed = road_data['speed_limit']
    self.lanes_available = road_data["num_lanes"]
    self.max_acceleration = road_data['max_acceleration']
    goal = road_data['goal']
    self.goal_lane = goal[1]
    self.goal_s = goal[0]

  """
  Method override to be used with `print`
  """
  def __repr__(self):
    s = "s:    {}\n".format(self.s)
    s +="lane: {}\n".format(self.lane)
    s +="v:    {}\n".format(self.v)
    s +="a:    {}\n".format(self.a)
    return s

  """
  Updates the vehicle state (s, v) based on delta_t=1
  """
  def increment(self, dt=1):
    self.s += self.v * dt
    self.v += self.a * dt

  """
  Peturns the predicted the state (s, v, a) of vehicle in t seconds (assuming constant acceleration)
  using motion model
  """
  def state_at(self, t):
    """
    Predicts state of vehicle in t seconds (assuming constant acceleration)
    """
    s = self.s + self.v * t + self.a * t * t / 2
    v = self.v + self.a * t
    return self.lane, s, v, self.a

  def collides_with(self, other, at_time=0):
    """
    Simple collision detection.
    """
    l,   s,   v,   a = self.state_at(at_time)
    l_o, s_o, v_o, a_o = other.state_at(at_time)
    return l == l_o and abs(s-s_o) <= L

  def will_collide_with(self, other, timesteps):
    for t in range(timesteps+1):
      if self.collides_with(other, t):
        return True, t
    return False, None

  """
  Given a state, realize it by adjusting acceleration and lane.
  Note - lane changes happen instantaneously.
  """
  def realize_state(self, predictions):
    """
    Given a state, realize it by adjusting acceleration and lane.
    Note - lane changes happen instantaneously.
    """
    state = self.state
    if   state == "CS"  : self.realize_constant_speed()
    elif state == "KL"  : self.realize_keep_lane(predictions)
    elif state == "LCL" : self.realize_lane_change(predictions, "L")
    elif state == "LCR" : self.realize_lane_change(predictions, "R")
    elif state == "PLCL": self.realize_prep_lane_change(predictions, "L")
    elif state == "PLCR": self.realize_prep_lane_change(predictions, "R")

  """
  Set acceleration zero to keep speed constant
  """
  def realize_constant_speed(self):
    self.a = 0

  """
  Decides how much to accelerate given vehicle based on predictions of
  other vehicles, self.v, self.target_speed, self.max_acceleration
  """
  def _max_accel_for_lane(self, predictions, lane, s):
    #calculate difference between current speed and target_speed
    delta_v_til_target = self.target_speed - self.v

    #Try to increase target_speed
    #Try to increase acceleration by delta_v_til_target but if it is not
    #possible then use max_acceleration as we can't exceed either target_speed
    #or max_acceleration
    max_acc = min(self.max_acceleration, delta_v_til_target)

    #From other vehicles predictions, identify and extract vehicles in front of given vehicle
    in_front = [v for (v_id, v) in predictions.items() if v[0]['lane'] == lane and v[0]['s'] > s ]

    #if there are vehicles in front of given vehicle then
    if len(in_front) > 0:
      #identify vehicle that is (directly infront) closest leading vehicle to the given vehicle
      leading = min(in_front, key=lambda v: v[0]['s'] - s)

      #find the position (`s` coordinate) of leading vehicle
      next_pos = leading[1]['s']

      #predict the position (`s` coordinate) of the given vehicle in next timestep
      #which is current position + vehicle speed
      my_next = s + self.v

      #find distance between the given vehicle and its leading vehicle
      separation_next = next_pos - my_next

      #we want to keep a buffer distance from the leading vehicle
      #so available distance between given vehicle and leading vehicle is
      #actually the total distance between the two vehicles minus the
      #preferred_buffer distance
      available_room = separation_next - self.preferred_buffer

      #if possible, accelerate vehicle to fill the available_room distance
      #between given vehicle and the vehicle leading it while making sure
      #we don't exceed target_speed and we keep a preferred_buffer distance
      max_acc = min(max_acc, available_room)

    return max_acc

  def realize_keep_lane(self, predictions):
    self.a = self._max_accel_for_lane(predictions, self.lane, self.s)

  """
  Note: Lane changes happen instantly so this method changes
  lane of the vehicle and updates its acceleration according to
  new lane traffic
  """
  def realize_lane_change(self, predictions, direction):
    #delta should be negative for left lane change
    #and positive for right.

    #initialize by default for left lane change
    delta = -1

    #make it positive for right lane change
    if direction == "R":
        delta = 1

    #change lane
    self.lane += delta
    #decide acceleration for new lane and based on vehicles in front
    self.a = self._max_accel_for_lane(predictions, self.lane, self.s)

  """
  This method update acceleration of vehicle to match its velocity with
  nearest_behind vehicle velocity
  """
  def realize_prep_lane_change(self, predictions, direction):
    delta = -1
    if direction == "L": delta = 1
    #pretend to be in new lane
    lane = self.lane + delta

    #extract vehicles in new lane that are behind given vehicle
    ids_and_vehicles = [(v_id, v) for (v_id, v) in predictions.items() if v[0]['lane'] == lane and v[0]['s'] <= self.s]

    #if there are any vehicles in new lane behind given vehicle
    if len(ids_and_vehicles) > 0:

      vehicles = [v[1] for v in ids_and_vehicles]

      #find vehicle details (vehicle_id, vehicle predictions)
      #of vehicle that is nearest behind current vehicle
      nearest_behind = max(ids_and_vehicles, key=lambda v: v[1][0]['s'])
      print("nearest behind : {}".format(nearest_behind))

      #extract only vehicle predictions from tupple (vehicle_id, vehicle_predictions)
      nearest_behind = nearest_behind[1]

      #find the velocity of nearest_behind vehicle
      #nearest_behind is actually predictions of that vehicle's
      #next predicted lane and position (`s` coordinate) so
      #subtracting that vehicles distance (`s coordinate`) at timestep=0
      #from distance at timestep=1 will give us its velocity
      target_vel = nearest_behind[1]['s'] - nearest_behind[0]['s']

      #find velocity and position difference of current vehicle
      #from nearest_behind vehicle (remember we are assuming in new lane so
      #nearest_behind vehicle is actually in new lane)
      delta_v = self.v - target_vel
      delta_s = self.s - nearest_behind[0]['s']

      #if current vehicle's speed is not same as nearest_behind vehicle's speed
      if delta_v != 0:
        print("delta_v {}".format(delta_v))
        print("delta_s {}".format(delta_s))

        #calculate time part of velocity
        time = -2 * delta_s / delta_v

        #if time part is 0 (delta_s is very small or delta_v is high) then
        #keep the current acceleration as nearest_behind vehicle has almost the
        #same acceleration
        if time == 0:
          a = self.a
        else:
          #use the same acceleration as of nearest_behind vehicle
          a = delta_v / time

        print("raw a is {}".format(a))

        #validate acceleration so that it remains within [-max_acceleration, max_acceleration]
        if a > self.max_acceleration: a = self.max_acceleration
        if a < -self.max_acceleration: a = -self.max_acceleration

        #assign this new calculated acceleration to given vehicle
        self.a = a
        print("time : {}".format(time))
        print("a: {}".format(self.a))
      else :
        #current vehicle and nearest_behind vehicle has same speed
        #so just decelerate current vehice so that we can cover
        #the distance difference delta_s
        min_acc = max(-self.max_acceleration, -delta_s)
        self.a = min_acc

  """
  Predicts state (s, v, a) of vehicle for given number of timesteps (horizon, by default 10)
  in seconds (assuming constant acceleration) and appends each predicted state
  to predictions dictionary
  """
  def generate_predictions(self, horizon=10):
    predictions = []
    for i in range(horizon):
      lane, s, v, a = self.state_at(i)
      predictions.append({'s':s, 'lane': lane})
    return predictions
