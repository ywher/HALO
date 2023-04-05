import warnings
import setproctitle
from core.utils.misc import mkdir, parse_args
from core.configs import cfg
from core.train_learners import TrainLearner
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers.wandb import WandbLogger
import argparse
import os
import sys
import pytorch_lightning as pl
import torch

cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)


warnings.filterwarnings('ignore')

torch.backends.cudnn.benchmark = True
# torch.use_deterministic_algorithms(True)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


def main():
    args = parse_args()
    print(args, end='\n\n')

    output_dir = cfg.OUTPUT_DIR
    if output_dir:
        mkdir(output_dir)

    setproctitle.setproctitle(f'{args.proctitle}')

    # init wandb logger
    wandb_logger = None
    if cfg.WANDB.ENABLE:
        wandb_logger = WandbLogger(project=cfg.WANDB.PROJECT, name=cfg.WANDB.NAME,
                                   entity=cfg.WANDB.ENTITY, group=cfg.WANDB.GROUP,
                                   config=cfg, save_dir='..')

    pl.seed_everything(cfg.SEED, workers=True)

    learner = TrainLearner(cfg)

    checkpoint_callback = ModelCheckpoint(
        save_top_k=1,
        monitor="mIoU",
        mode="max",
        dirpath=cfg.OUTPUT_DIR,
        filename="model_{epoch:02d}_{mIoU:.2f}",
    )

    # init trainer
    trainer = pl.Trainer(
        accelerator='gpu',
        devices=cfg.SOLVER.GPUS,
        max_epochs=1000,
        max_steps=cfg.SOLVER.STOP_ITER,
        log_every_n_steps=20,
        accumulate_grad_batches=1,
        sync_batchnorm=True,
        strategy="ddp",
        num_nodes=1,
        logger=wandb_logger,
        callbacks=[checkpoint_callback],
        check_val_every_n_epoch=1,
        val_check_interval=1000,
        precision=32,
        detect_anomaly=True)

    # start training
    trainer.fit(learner)


if __name__ == '__main__':
    main()