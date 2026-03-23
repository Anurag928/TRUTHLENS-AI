import os, torch, warnings
warnings.filterwarnings("ignore")

p = os.path.join(os.path.dirname(__file__), 'models', 'Model 97 Accuracy 100 Frames FF Data.pt')
ck = torch.load(p, map_location='cpu')
for k, v in sorted(ck.items()):
    print(f"{k}: {list(v.shape)}")
