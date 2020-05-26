import os
import json
import pandas as pd
from multiprocessing import cpu_count

from transquest.util.normalizer import fit
from transquest.algo.transformers.utils import InputExample


DEFAULT_FEATURE_NAME = 'feature'


def load_config(args):
    config = json.load(open(args.config))
    process_count = cpu_count() - 2 if cpu_count() > 2 else 1
    config.update({
        'output_dir': os.path.join(args.output_dir, 'outputs'),
        'best_model_dir': os.path.join(args.output_dir, 'best_model'),
        'cache_dir': os.path.join(args.output_dir, 'cache_dir'),
        'process_count': process_count,
    })
    return config


def load_examples(df):
    if "text_a" in df.columns and "text_b" in df.columns:
        examples = [
            InputExample(i, text_a, text_b, label)
            for i, (text_a, text_b, label) in enumerate(
                zip(df["text_a"], df["text_b"], df["labels"])
            )
        ]
    else:
        raise ValueError(
            "Passed DataFrame is not in the correct format. Please rename your columns to text_a, text_b and labels"
        )
    if "{}1".format(DEFAULT_FEATURE_NAME) in df.columns:
        for col in df.columns:
            if col.startswith(DEFAULT_FEATURE_NAME):
                values = df[col].to_list()
                for i, ex in enumerate(examples):
                    ex.features_inject[col] = values[i]
    return examples


def read_data_file(fpath, split=None, features_pref=None):
    select_columns = ['original', 'translation', 'z_mean']
    data = pd.read_csv(fpath, sep='\t', quoting=3)
    data = data[select_columns]
    data = data.rename(columns={'original': 'text_a', 'translation': 'text_b', 'z_mean': 'labels'})
    data = fit(data, 'labels')

    if features_pref is not None:
        features = pd.read_csv(features_pref + '.{}.tsv'.format(split), sep='\t', header=None)
        num_features = len(features.columns)
        features.columns = ['{}{}'.format(DEFAULT_FEATURE_NAME, i) for i in range(1, num_features + 1)]
        assert len(features) == len(data)
        for column in features.columns:
            data[column] = features[column]

    return data


def read_data_files(train_file, test_file, features_pref=None):
    train = read_data_file(train_file, split='train', features_pref=features_pref)
    test = read_data_file(test_file, split='test', features_pref=features_pref)
    assert list(train.columns) == list(test.columns)
    return train, test
