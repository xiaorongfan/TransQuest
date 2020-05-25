import argparse
import os
import shutil

import numpy as np
import torch

from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from transquest.algo.transformers.evaluation import pearson_corr, spearman_corr
from transquest.algo.transformers.run_model import QuestModel
from transquest.util.draw import draw_scatterplot

from transquest.util.data import read_data_files
from transquest.util.data import load_config
from transquest.util.normalizer import un_fit


def train_model(train_set, config, n_fold=None, test_size=None, return_model=False):
    seed = config['SEED'] * n_fold if n_fold else config['SEED']
    model = QuestModel(
        config['MODEL_TYPE'], config['MODEL_NAME'], num_labels=1, use_cuda=torch.cuda.is_available(), args=config,)
    if test_size:
        train_n, eval_df_n = train_test_split(train_set, test_size=test_size, random_state=seed)
    else:
        train_n = train_set
        eval_df_n = None
    model.train_model(
        train_n, eval_df=eval_df_n, pearson_corr=pearson_corr, spearman_corr=spearman_corr, mae=mean_absolute_error)
    if return_model:
        return model


def evaluate_model(test_set, config, model=None):
    if model is None:
        model = QuestModel(
            config['MODEL_TYPE'], config['best_model_dir'], num_labels=1, use_cuda=torch.cuda.is_available(),
            args=config
        )
    _, model_outputs, _ = model.eval_model(
        test_set, pearson_corr=pearson_corr, spearman_corr=spearman_corr, mae=mean_absolute_error
    )
    return model_outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train_path', required=True)
    parser.add_argument('--test_path', required=True)
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--features_pref', default=None, required=False)
    parser.add_argument('--test_size', default=0.1, type=float)
    args = parser.parse_args()
    config = load_config(args)
    train, test = read_data_files(args.train_path, args.test_path, features_pref=args.features_pref)
    if config['evaluate_during_training']:
        if config['n_fold'] > 1:
            test_preds = np.zeros((len(test), config['n_fold']))
            for i in range(config['n_fold']):
                print('Training with N folds. Now N is {}'.format(i))
                if os.path.exists(config['output_dir']) and os.path.isdir(config['output_dir']):
                    shutil.rmtree(config['output_dir'])
                train_model(train, config, n_fold=i, test_size=args.test_size)
                model_outputs = evaluate_model(test, config)
                test_preds[:, i] = model_outputs
            test['predictions'] = test_preds.mean(axis=1)
        else:
            train_model(train, config, test_size=args.test_size)
            model_outputs = evaluate_model(test, config)
            test['predictions'] = model_outputs
    else:
        model = train_model(train, config, return_model=True)
        model_outputs = evaluate_model(test, config, model=model)
        test['predictions'] = model_outputs

    test = un_fit(test, 'labels')
    test = un_fit(test, 'predictions')
    test.to_csv(os.path.join(args.output_dir, 'results.tsv'), header=True, sep='\t', index=False, encoding='utf-8')
    draw_scatterplot(test, 'labels', 'predictions', os.path.join(args.output_dir, 'results.png'),
                     config['MODEL_TYPE'] + ' ' + config['MODEL_NAME'])


if __name__ == '__main__':
    main()