

import os

import datetime
import numpy as np
import json
import multiprocessing
import time

import sys

from MinitaggerSVM import MinitaggerSVM

sys.path.insert(0, 'helper')

from Minitagger import Minitagger
from SequenceData import SequenceData
from utils import create_recursive_folder

from MinitaggerCRF import MinitaggerCRF
from FeatureExtractor_CRF_SVM import FeatureExtractor_CRF_SVM


class final_training(object):
    def __init__(self,train_data_path, validation_data_path, test_data_path, language, model_name,
                                feature_template, embedding_size=None, embedding_path=None, CV=10):
        self.validation_data_path = validation_data_path
        self.train_data_path = train_data_path
        self.test_data_path = test_data_path
        self.minitagger = None
        self.language = language
        self.model_name = model_name
        self.feature_template = feature_template
        self.embedding_size = embedding_size
        self.embedding_path = embedding_path
        self.CV = CV

        create_recursive_folder(["parameters", model_name])
        self.display_info(language, model_name, feature_template, embedding_size, embedding_path)



    def final_training(self,method, best_param=None, train_with_step=False):
        infos = dict()
        infos["method"] = method
        infos["train_data_path"] = self.train_data_path
        infos["test_data_path"] = self.test_data_path
        infos["language"] = self.language
        infos["mpdel_name"] = self.model_name
        infos["feature_template"] = self.feature_template
        infos["embedding_size"] = self.embedding_size
        infos["embedding_path"] = self.embedding_path

        # initialize feature extractor with the right feature template
        self.feature_extractor = FeatureExtractor_CRF_SVM(self.feature_template, self.language,
                                                         self.embedding_size if self.embedding_size else None)

        self.train_sequence = SequenceData(self.train_data_path,language=self.language, pos_tag=True)
        self.validation_sequence = SequenceData(self.validation_data_path,language=self.language, pos_tag=True) if self.validation_data_path is not None else None
        self.test_sequence = SequenceData(self.test_data_path,language=self.language, pos_tag=True)

        # load bitstring or embeddings data
        if self.feature_template == "embedding":
            self.feature_extractor.load_word_embeddings(self.embedding_path, self.embedding_size)

        print("Number of sentences in training dataset:", len(self.train_sequence.sequence_pairs))
        print("Number of sentences in testing dataset:", len(self.test_sequence.sequence_pairs))
        if method is "CRF":
            self.crf(best_param, train_with_step)
        elif method is "SVM":
            self.svm(best_param, train_with_step)

    def crf(self,best_param, train_with_step=False):
        self.minitagger = MinitaggerCRF()
        self.minitagger.language = self.language
        self.minitagger.quiet = True

        self.minitagger.set_prediction_path(self.model_name)
        self.minitagger.set_model_path(self.model_name)


        # equip Minitagger with the appropriate feature extractor
        self.minitagger.equip_feature_extractor(self.feature_extractor)

        self.minitagger.algorithm = "lbfgs"
        if best_param is not None:
            self.minitagger.c1 = best_param['c1']
            self.minitagger.c2 = best_param['c2']
            self.minitagger.epsilon = best_param['epsilon']
        else:
            self.minitagger.c1 = 0.1282051282051282
            self.minitagger.c2 = 0.23076923076923075
            self.minitagger.epsilon =0.0008376776400682924

        self.minitagger.all_possible_state = True
        self.minitagger.all_possible_transitions = True

        parameter = dict()
        parameter["algo"] = self.minitagger.algorithm
        parameter["c1"] = self.minitagger.c1
        parameter["c2"] = self.minitagger.c2
        parameter["epsilon"] = self.minitagger.epsilon
        parameter["all_possible_states"] = self.minitagger.all_possible_state
        parameter["all_possible_transition"] = self.minitagger.all_possible_transitions

        self.minitagger.extract_features(self.train_sequence, self.test_sequence, self.validation_sequence)
        if train_with_step:
            self.minitagger.train_with_step()
        else:
            self.minitagger.quiet = False
            self.minitagger.train()


    def svm(self, best_param, train_with_step=False):
        self.minitagger = MinitaggerSVM()
        self.minitagger.language = self.language
        self.minitagger.quiet = True
        self.minitagger.equip_feature_extractor(self.feature_extractor)
        self.minitagger.set_prediction_path(self.model_name)
        self.minitagger.set_model_path(self.model_name)

        parameter = dict()
        if best_param is not None:
            self.minitagger.epsilon = best_param['epsilon']
            self.minitagger.cost = best_param['cost']
        else:
            self.minitagger.epsilon =0.153617494667
            self.minitagger.cost = 17.9571449437
        parameter["epsilon"] = self.minitagger.epsilon
        parameter["cost"] = self.minitagger.cost

        if train_with_step:
            self.minitagger.train_with_step(self.train_sequence, self.test_sequence)
        else:
            self.minitagger.extract_features(self.train_sequence, self.test_sequence)
            self.minitagger.quiet=False
            self.minitagger.train()
            self.minitagger.save(self.minitagger.model_path)

    @staticmethod
    def display_results(conll_fscore, conll_precision, conll_recall, conll_parameters):
        print()
        print()
        print("=================================")
        print("Results")
        print("=================================")
        print("F1score", conll_fscore)
        # print("Std", conll_stds)
        print()
        print("=================================")
        print("Best results")
        print("=================================")
        argmax = np.argmax(conll_fscore)
        print(" Best conll f1score:", conll_fscore[argmax])
        print(" Corresponding conll precision:", conll_precision[argmax])
        print(" Corresponding conll recall:", conll_recall[argmax])
        print(" Corresponding id:", argmax)
        # print(" Correspondind std:", conll_stds[argmax])
        print(" Corresponding parameters:", conll_parameters[argmax])

    @staticmethod
    def display_info(number_of_sentence, language, model_name, feature_template, embedding_size=None,
                     embedding_path=None):
        print("Number of sentences: ", number_of_sentence)
        print("Language: ", language)
        print("Model name: ", model_name)
        print("Feature template:", feature_template)
        if feature_template == "embedding":
            print("Embedding size: ", embedding_size)

    def save_to_file(self, conll_fscore, conll_precision, conll_recall, conll_parameters, infos, model_name):
        argmax = np.argmax(conll_fscore)
        with open(os.path.join(self.minitagger.model_path, "best_conll_param.json"),
                  "w") as file:  # TODO change path => put everything in model folder
            conll = dict()
            conll["fscore"] = conll_fscore[argmax]
            conll["precision"] = conll_precision[argmax]
            conll["recall"] = conll_recall[argmax]
            # conll["std"] = conll_stds[argmax]
            conll["parameter"] = conll_parameters[argmax]
            conll["list_fscore"] = conll_fscore
            conll["list_precision"] = conll_precision
            conll["list_recall"] = conll_recall
            # conll["list_std"] = conll_stds
            conll["list_parameter"] = conll_parameters

            json_data = {"infos": infos, "results": conll}
            json.dump(json_data, file, indent=2, separators=(',', ': '))


if __name__ == "__main__":

    a = "new_dataset"
    language = "en"
    embedding_size = 300
    if a == "new_dataset":
        train_data_path = "../../new_dataset/combined_100000.txt"
        validation_data_path = "../../ner/nerc-conll2003/eng-simplified.testa"
        test_data_path = "../../ner/nerc-conll2003/eng-simplified.testb"
        feature_template = "baseline"
        embedding_path = "../../word_embeddings/glove"
        method = "SVM"

        model_name = "_new_dataset_finale_score"

    elif a == "wikiner":
        train_data_path = "../../wikiner_dataset/aij-wikiner-en-wp2-simplified"
        #train_data_path = "../../ner/nerc-conll2003/eng-simplified.train"
        validation_data_path = "../../ner/nerc-conll2003/eng-simplified.testa"
        test_data_path = "../../ner/nerc-conll2003/eng-simplified.testb"
        feature_template = "baseline"
        embedding_path = "../../word_embeddings/fasttext"
        #model_name = "SVM_wikiner_emb" + str(embedding_size) + "_finale_score"
        model_name = "_wikiner_baseline_finale_score"
        method = "SVM"
    elif a == "conll":
        train_data_path = "../../ner/nerc-conll2003/eng-simplified.train"
        validation_data_path = "../../ner/nerc-conll2003/eng-simplified.testa"
        test_data_path = "../../ner/nerc-conll2003/eng-simplified.testb"
        #feature_template = "embedding"
        feature_template = "baseline"
        embedding_path = "../../word_embeddings/fasttext"
        embedding_size = 300
        method = "SVM"
        model_name = method + "_conll_emb" + str(embedding_size) + "_finale_score"


    selection = final_training(train_data_path, validation_data_path, test_data_path, language, model_name,
                                      feature_template, embedding_size, embedding_path)

    # elif algorithm == "CRF":
    selection.final_training(method)


    # if algorithm == "SVM":
    # model_name = "SVM_wikiner_emb"+str(embedding_size)+"_parameter_selection_1"
    # parameter_selection_svm(train_data_path,test_data_path, language, model_name, feature_template, embedding_size,embedding_path)
