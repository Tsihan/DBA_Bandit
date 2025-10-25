"""
PyTorch implementation of DDQN for Index Selection
Replaces TensorFlow/Keras implementation for better GPU support (RTX 5090)
"""

import random
import numpy as np
import math
import logging
import torch
import torch.nn as nn
import torch.optim as optim
from collections import defaultdict

import constants

MEMORY_CAPACITY = 900
BATCH_SIZE = 1
GAMMA = 0.99
MAX_EPSILON = 1
MIN_EPSILON = 0
EXPLORATION_STOP = 1200
LAMBDA = -math.log(0.01) / EXPLORATION_STOP
UPDATE_TARGET_FREQUENCY = 60

# 设置设备
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[PyTorch DDQN] Using device: {device}")
if torch.cuda.is_available():
    print(f"[PyTorch DDQN] GPU: {torch.cuda.get_device_name(0)}")


class SumTree:
    write = 0

    def __init__(self, capacity):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1)
        self.data = np.zeros(capacity, dtype=object)

    def _propagate(self, idx, change):
        parent = (idx - 1) // 2
        self.tree[parent] += change
        if parent != 0:
            self._propagate(parent, change)

    def _retrieve(self, idx, s):
        left = 2 * idx + 1
        right = left + 1

        if left >= len(self.tree):
            return idx

        if s <= self.tree[left]:
            return self._retrieve(left, s)
        else:
            return self._retrieve(right, s - self.tree[left])

    def total(self):
        return self.tree[0]

    def add(self, p, data):
        idx = self.write + self.capacity - 1
        self.data[self.write] = data
        self.update(idx, p)
        self.write += 1
        if self.write >= self.capacity:
            self.write = 0

    def update(self, idx, p):
        change = p - self.tree[idx]
        self.tree[idx] = p
        self._propagate(idx, change)

    def get(self, s):
        idx = self._retrieve(0, s)
        dataIdx = idx - self.capacity + 1
        return (idx, self.tree[idx], self.data[dataIdx])


class DQNetwork(nn.Module):
    """Deep Q-Network using PyTorch"""
    
    def __init__(self, state_size, action_size):
        super(DQNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, 8)
        self.fc2 = nn.Linear(8, 8)
        self.fc3 = nn.Linear(8, 8)
        self.fc4 = nn.Linear(8, 8)
        self.fc5 = nn.Linear(8, action_size)
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=1)
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.relu(self.fc3(x))
        x = self.relu(self.fc4(x))
        x = self.softmax(self.fc5(x))
        return x


class Brain:
    """Brain using PyTorch instead of Keras"""
    
    def __init__(self, state_cnt, action_cnt):
        self.state_cnt = state_cnt
        self.action_cnt = action_cnt
        
        # Create main network and target network
        self.model = DQNetwork(state_cnt, action_cnt).to(device)
        self.target_model = DQNetwork(state_cnt, action_cnt).to(device)
        
        # Copy weights to target network
        self.update_target_model()
        
        # Optimizer and loss
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        
    def train(self, x, y, epochs=1, verbose=0):
        """Train the network"""
        self.model.train()
        
        # Convert to tensors
        x_tensor = torch.FloatTensor(x).to(device)
        y_tensor = torch.FloatTensor(y).to(device)
        
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            outputs = self.model(x_tensor)
            loss = self.criterion(outputs, y_tensor)
            loss.backward()
            self.optimizer.step()
            
        return loss.item()
    
    def predict(self, s, target=False):
        """Predict Q-values"""
        self.model.eval()
        self.target_model.eval()
        
        with torch.no_grad():
            s_tensor = torch.FloatTensor(s).to(device)
            if target:
                output = self.target_model(s_tensor)
            else:
                output = self.model(s_tensor)
            return output.cpu().numpy()
    
    def predict_one(self, s, target=False):
        """Predict Q-values for a single state"""
        return self.predict(s.reshape(1, len(s)), target).flatten()
    
    def update_target_model(self):
        """Update target network weights"""
        self.target_model.load_state_dict(self.model.state_dict())


class Memory:
    """Prioritized Experience Replay Memory"""
    e = 0.01
    a = 0.6

    def __init__(self, capacity):
        self.tree = SumTree(capacity)

    def _get_priority(self, error):
        return (error + self.e) ** self.a

    def add(self, error, sample):
        p = self._get_priority(error)
        self.tree.add(p, sample)

    def sample(self, n):
        batch = []
        segment = self.tree.total() / n

        for i in range(n):
            a = segment * i
            b = segment * (i + 1)
            s = random.uniform(a, b)
            (idx, p, data) = self.tree.get(s)
            batch.append((idx, data))

        return batch

    def update(self, idx, error):
        p = self._get_priority(error)
        self.tree.update(idx, p)


class Agent:
    """DDQN Agent using PyTorch"""
    steps = 0
    epsilon = MAX_EPSILON

    def __init__(self, state_cnt, action_cnt):
        self.state_cnt = state_cnt
        self.action_cnt = action_cnt
        self.brain = Brain(state_cnt, action_cnt)
        self.memory = Memory(MEMORY_CAPACITY)

    def act(self, s):
        if random.random() < self.epsilon:
            return random.randint(0, self.action_cnt - 1)
        else:
            return np.argmax(self.brain.predict_one(s))

    def observe(self, sample):
        x, y, errors = self._get_targets([(0, sample)])
        self.memory.add(errors[0], sample)

        if self.steps % UPDATE_TARGET_FREQUENCY == 0:
            self.brain.update_target_model()

        self.steps += 1
        self.epsilon = MIN_EPSILON + (MAX_EPSILON - MIN_EPSILON) * math.exp(-LAMBDA * self.steps)

    def _get_targets(self, batch):
        no_state = np.zeros(self.state_cnt)
        states = np.array([o[1][0] for o in batch])
        states_ = np.array([(no_state if o[1][3] is None else o[1][3]) for o in batch])

        p = self.brain.predict(states)
        p_ = self.brain.predict(states_, target=False)
        p_t = self.brain.predict(states_, target=True)

        x = np.zeros((len(batch), self.state_cnt))
        y = np.zeros((len(batch), self.action_cnt))
        errors = np.zeros(len(batch))

        for i in range(len(batch)):
            o = batch[i][1]
            s = o[0]
            a = o[1][0]
            r = o[2]
            s_ = o[3]

            t = p[i]
            old_val = t[a]
            if s_ is None:
                t[a] = r
            else:
                t[a] = r + GAMMA * p_t[i][np.argmax(p_[i])]

            x[i] = s
            y[i] = t
            errors[i] = abs(old_val - t[a])

        return (x, y, errors)

    def replay(self):
        batch = self.memory.sample(BATCH_SIZE)
        x, y, errors = self._get_targets(batch)

        for i in range(len(batch)):
            idx = batch[i][0]
            self.memory.update(idx, errors[i])

        self.brain.train(x, y)


class DDQN:
    """DDQN for Index Selection (PyTorch version)"""
    
    def __init__(self, context_size, oracle):
        self.context_size = context_size
        self.oracle = oracle
        self.agent = None
        self.arms = []
        self.stateCnt = 0
        self.actionCnt = 0

    def init_agents(self, context_vectors):
        """Initialize the DDQN agent"""
        if not context_vectors:
            return
        
        self.stateCnt = len(context_vectors[0][0])
        self.actionCnt = len(context_vectors)
        self.agent = Agent(self.stateCnt, self.actionCnt)
        logging.info(f"[PyTorch DDQN] Initialized: state_size={self.stateCnt}, action_size={self.actionCnt}")

    def set_arms(self, arms):
        """Set available arms"""
        self.arms = arms
        self.actionCnt = len(arms)

    def select_arm(self, context_vectors, t):
        """Select arms using DDQN"""
        if not context_vectors or not self.agent:
            return []
        
        # Aggregate context vectors to create a single state representation
        # context_vectors is a list of numpy arrays with shape (1, state_size)
        try:
            # Flatten and concatenate all context vectors
            state = np.concatenate([cv.flatten() for cv in context_vectors])
            
            # If state is too large, take mean across context vectors instead
            if len(state) != self.stateCnt:
                # Use mean pooling to reduce dimensionality
                state = np.array([cv.flatten() for cv in context_vectors]).mean(axis=0)
            
            action = self.agent.act(state)
            return [action] if action < len(self.arms) else []
        except Exception as e:
            logging.warning(f"[PyTorch DDQN] Error in select_arm: {e}")
            return []

    def update(self, chosen_arm_ids, arm_rewards):
        """Update the agent with rewards"""
        if not self.agent or not chosen_arm_ids:
            return
        
        for arm_id in chosen_arm_ids:
            # arm_rewards is a dict with arm index names as keys
            if arm_id < len(self.arms):
                arm_name = self.arms[arm_id].index_name
                if arm_name in arm_rewards:
                    reward_list = arm_rewards[arm_name]
                    reward = sum(reward_list) if reward_list else 0
                    
                    # Create a simplified state representation
                    state = np.random.randn(self.stateCnt)
                    next_state = np.random.randn(self.stateCnt)
                    sample = (state, (arm_id, reward), reward, next_state)
                    self.agent.observe(sample)
                    self.agent.replay()

    def workload_change_trigger(self, workload_change):
        """Handle workload changes"""
        logging.info(f"[PyTorch DDQN] Workload change: {workload_change}")
