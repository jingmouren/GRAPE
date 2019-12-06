import numpy as np
import torch
import matplotlib.pyplot as plt
import argparse
from utils import objectview

parser = argparse.ArgumentParser()
parser.add_argument('--file', type=str, default='1')
args = parser.parse_args()

load_path = './Data/uci/'+args.file+'/'

import joblib
result = joblib.load(load_path+'result.pkl')
result = objectview(result)
train_args = result.args
for key in train_args.__dict__.keys():
    print(key,': ',train_args.__dict__[key])

from plot_utils import plot_result
plot_result(result, load_path)

from uci import UCIDataset
dataset = UCIDataset(root='/tmp/UCI')
from torch_geometric.data import DataLoader
loader = DataLoader(dataset, batch_size=train_args.batch_size, shuffle=True)

if train_args.gnn_type == 'GNN':
    from models2 import GNNStack
    model_cls = GNNStack
elif train_args.gnn_type == 'GNN_SPLIT':
    from models3 import GNNStackSplit
    model_cls = GNNStackSplit
model = model_cls(dataset.num_node_features, train_args.node_dim,
                        train_args.edge_dim, train_args.edge_mode,
                        train_args.predict_mode,
                        (train_args.update_edge==1),
                        train_args)
model.load_state_dict(torch.load(load_path+'model.pt'))
model.eval()

for data in loader:
    if train_args.load_train_mask == 1:
        print('loading train validation mask')
        train_mask = np.load(train_args.train_mask_dir)
        train_mask = torch.BoolTensor(train_mask).view(-1)
    else:
        print('defining train validation mask')
        train_mask = (torch.FloatTensor(int(data.edge_attr.shape[0]/2), 1).uniform_() < (1-train_args.valid)).view(-1)
    train_mask = torch.cat((train_mask, train_mask),dim=0)
    valid_mask = ~train_mask
    mask_defined = True

    x = torch.FloatTensor(np.copy(data.x))
    edge_attr = data.edge_attr.clone().detach()
    edge_index = torch.tensor(np.copy(data.edge_index),dtype=int)


    if train_args.remove_unknown_edge == 1:
        train_edge_index = edge_index[:,train_mask]
        train_edge_attr = edge_attr[train_mask]
    else:
        train_edge_index = edge_index
        train_edge_attr = edge_attr.clone().detach()
        train_edge_attr[valid_mask] = 0.

    xs, preds = model(x, train_edge_attr, train_edge_index, edge_index, return_x=True)
    Os = {}
    for indx in range(128):
        i=edge_index[0,indx].detach().numpy()
        j=edge_index[1,indx].detach().numpy()
        true=train_edge_attr[indx].detach().numpy()
        pred=preds[indx].detach().numpy()
        xi=xs[i].detach().numpy()
        xj=xs[j].detach().numpy()
        if str(i) not in Os.keys():
            Os[str(i)] = {'true':[],'pred':[],'x_j':[]}
        Os[str(i)]['true'].append(true)
        Os[str(i)]['pred'].append(pred)
        Os[str(i)]['x_i'] = xi
        Os[str(i)]['x_j'] += list(xj)

import matplotlib.pyplot as plt
plt.figure()
plt.subplot(1,3,1)
for i in Os.keys():
    plt.plot(Os[str(i)]['pred'],label='o'+str(i)+'pred')
plt.legend()
plt.subplot(1,3,2)
for i in Os.keys():
    plt.plot(Os[str(i)]['x_i'],label='o'+str(i)+'xi')
    # print(Os[str(i)]['x_i'])
plt.legend()
plt.subplot(1,3,3)
for i in Os.keys():
    plt.plot(Os[str(i)]['x_j'],label='o'+str(i)+'xj')
    # print(Os[str(i)]['x_j'])
plt.legend()
plt.savefig(load_path+'check_embedding.png')

