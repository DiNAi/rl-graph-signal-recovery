import numpy as np
import tensorflow as tf
from gym.spaces import Box, MultiBinary
from baselines import deepq
from baselines.common import tf_util
from baselines.common.schedules import LinearSchedule
from baselines.deepq.replay_buffer import ReplayBuffer

from algorithms.recovery import sparse_label_propagation
from graph_functions import nmse

class BaseAgent(object):
  def __init__(self, env):
    self.env = env
    self._build_train()
    self.session = tf_util.make_session(1)

  def _build_train(self):
    env = self.env

    def observation_ph_generator(name):
      if isinstance(env.observation_space, MultiBinary):
        batch_shape = (env.observation_space.n,)
      elif isinstance(env.observation_space, Box):
        batch_shape = env.observation_space.shape
      return tf_util.BatchInput(batch_shape, name=name)

    act, train, update_target, debug = deepq.build_train(
      make_obs_ph=observation_ph_generator,
      q_func=deepq.models.mlp([100]),
      num_actions=env.action_space.n,
      optimizer=tf.train.AdamOptimizer(learning_rate=1),
    )
    self.act = act
    self.train = train
    self.update_target = update_target
    self.debug = debug

  def learn(self, num_train_graphs=100):
    env = self.env

    act = self.act
    train = self.train
    update_target = self.update_target

    with self.session.as_default():
      # Create the replay buffer
      replay_buffer = ReplayBuffer(10)
      # Create the schedule for exploration starting from 1 (every action is random) down to
      # 0.02 (98% of actions are selected according to values predicted by the model).
      exploration = LinearSchedule(schedule_timesteps=1000,
                                   initial_p=1.0,
                                   final_p=0.02)

      tf_util.initialize()
      update_target()

      episode_rewards = [0.0]
      observation = env.reset()

      for t in range(num_train_graphs):
        done = False
        while not done:
          # Take action and update exploration to the newest value
          action = act(observation[None], update_eps=exploration.value(t))[0]
          new_observation, reward, done, _ = env.step(action)
          # Store transition in the replay buffer.
          replay_buffer.add(observation, action, reward,
                            new_observation, float(done))
          observation = new_observation

          episode_rewards[-1] += reward

          if done:
            if len(episode_rewards) % 10 == 0:
              nmse = env.get_current_nmse()
              print("steps", t)
              print("episodes", len(episode_rewards))
              print("mean episode reward", round(np.mean(episode_rewards[-101:-1]), 1))
              print("nmse: ", nmse)
              print("% time spent exploring", int(100 * exploration.value(t)))

            observation = env.reset()
            episode_rewards.append(0)

          is_solved = False
          if is_solved:
            # Show off the result
            env.render()
          else:
            # Minimize the Bellman equation error on replay buffer sample batch
            if t > 1000:
              (observations_t, actions, rewards,
               observations_tp1, dones) = replay_buffer.sample(32)
              train(observations_t, actions, rewards,
                    observations_tp1, dones, np.ones_like(rewards))
            if t % 1000 == 0:
              # Update target network periodically.
              update_target()

  def test(self):
    env = self.env
    act = self.act
    train = self.train
    update_target = self.update_target

    with self.session.as_default():
      observation, done = env.reset(), False
      while not done:
        action = act(observation[None], update_eps=0.9)[0]
        observation, reward, done, _ = env.step(action)

    nmse = env.get_current_nmse()
    print("nmse: ", nmse)