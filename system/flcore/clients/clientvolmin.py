import torch
import torch.nn as nn
import numpy as np
import time
from flcore.clients.clientbase import Client
from utils.privacy import *
from flcore.trainmodel.models import trans


class clientVolMin(Client):
    def __init__(self, args, id, train_samples, test_samples, **kwargs):
        super().__init__(args, id, train_samples, test_samples, **kwargs)

        self.lam = args.lambda_t
        self.trans = trans(args.device, args.num_classes)
        self.loss = nn.NLLLoss()
        self.optimizer = torch.optim.SGD([{'params': self.model.parameters()},
                                          {'params': self.trans.parameters()}
                                          ], lr=self.learning_rate)

        # differential privacy
        if self.privacy:
            check_dp(self.model)
            initialize_dp(self.model, self.optimizer, self.sample_rate, self.dp_sigma)

    def train(self):
        trainloader = self.load_train_data()

        start_time = time.time()

        # self.model.to(self.device)
        self.model.train()
        self.trans.train()

        max_local_steps = self.local_steps
        if self.train_slow:
            max_local_steps = np.random.randint(1, max_local_steps // 2)

        for step in range(max_local_steps):
            for i, (x, y) in enumerate(trainloader):
                if type(x) == type([]):
                    x[0] = x[0].to(self.device)
                else:
                    x = x.to(self.device)
                y = y.to(self.device)
                if self.train_slow:
                    time.sleep(0.1 * np.abs(np.random.rand()))
                self.optimizer.zero_grad()
                output = self.model(x)
                clean = torch.softmax(output, dim=1)
                t = self.trans()

                output = torch.mm(clean, t)

                vol_loss = t.slogdet().logabsdet
                # print(t)
                # print(vol_loss)
                loss = self.loss(torch.log(output), y) + self.lam * vol_loss
                loss.backward()
                if self.privacy:
                    dp_step(self.optimizer, i, len(trainloader))
                else:
                    self.optimizer.step()

        # self.model.cpu()

        self.train_time_cost['num_rounds'] += 1
        self.train_time_cost['total_cost'] += time.time() - start_time

        if self.privacy:
            res, DELTA = get_dp_params(self.optimizer)
            print(f"Client {self.id}", f"(ε = {res[0]:.2f}, δ = {DELTA}) for α = {res[1]}")

    def test_metrics(self):
        T = self.trans()
        print(self.lam)
        print(T)
        return super().test_metrics()

    def train_metrics(self):
        trainloader = self.load_train_data()
        # self.model = self.load_model('model')
        # self.model.to(self.device)
        self.model.eval()
        self.trans.eval()

        train_num = 0
        loss = 0
        for x, y in trainloader:
            if type(x) == type([]):
                x[0] = x[0].to(self.device)
            else:
                x = x.to(self.device)
            y = y.to(self.device)
            output = self.model(x)
            output = torch.softmax(output, dim=1)
            t = self.trans()

            output = torch.mm(output, t)
            # print('------------train------------')
            # self.save_demo(x, output, y)
            train_num += y.shape[0]
            # print('------loss:------')
            # print(self.loss(torch.log(output), y))
            # print(output[0])
            # print('------------')
            loss += self.loss(torch.log(output), y).item() * y.shape[0]

        # self.model.cpu()
        # self.save_model(self.model, 'model')

        return loss, train_num