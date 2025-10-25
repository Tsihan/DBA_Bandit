"""
Quick test for PyTorch DDQN
"""
import torch
import numpy as np
from bandits.rl_ddqn_pytorch import Brain, Agent, DDQN

print("="*80)
print("PyTorch DDQN Test")
print("="*80)

# Test device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\nDevice: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Version: {torch.version.cuda}")

# Test Brain
print("\n[1] Testing Brain (DQN Network)...")
brain = Brain(state_cnt=10, action_cnt=5)
print(f"    ✓ Created brain with state_size=10, action_size=5")
print(f"    ✓ Model on device: {next(brain.model.parameters()).device}")

# Test prediction
test_state = np.random.randn(10)
pred = brain.predict_one(test_state)
print(f"    ✓ Prediction shape: {pred.shape}, sum: {pred.sum():.4f}")

# Test training
x_train = np.random.randn(4, 10)
y_train = np.random.randn(4, 5)
loss = brain.train(x_train, y_train)
print(f"    ✓ Training loss: {loss:.6f}")

# Test Agent
print("\n[2] Testing Agent...")
agent = Agent(state_cnt=10, action_cnt=5)
print(f"    ✓ Created agent")

# Test action selection
action = agent.act(test_state)
print(f"    ✓ Selected action: {action}")

# Test observation
sample = (test_state, (action, 1.0), 1.0, test_state)
agent.observe(sample)
print(f"    ✓ Observed sample, epsilon: {agent.epsilon:.4f}")

# Test DDQN
print("\n[3] Testing DDQN...")
class MockOracle:
    pass

ddqn = DDQN(context_size=10, oracle=MockOracle())

# Test with context vectors
context_vectors = [np.random.randn(1, 10) for _ in range(5)]
ddqn.init_agents(context_vectors)
print(f"    ✓ Initialized DDQN: state={ddqn.stateCnt}, actions={ddqn.actionCnt}")

# Test GPU memory usage
if torch.cuda.is_available():
    print(f"\n[GPU] Memory allocated: {torch.cuda.memory_allocated()/1024**2:.2f} MB")
    print(f"[GPU] Memory reserved: {torch.cuda.memory_reserved()/1024**2:.2f} MB")

print("\n" + "="*80)
print("✅ All tests passed! PyTorch DDQN is ready.")
print("="*80)
