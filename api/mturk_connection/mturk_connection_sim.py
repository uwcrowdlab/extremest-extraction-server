from app import app
import sys
from mturk_connection import MTurk_Connection
from api.crowdjs_util import get_next_assignment, submit_answer, get_answers
from api.util import parse_answers
from api.ml.extractors.cnn_core.train import train_cnn
from api.ml.extractors.cnn_core.test import test_cnn
from random import shuffle
import uuid
import pickle
import json
from schema.job import Job
from schema.experiment import Experiment
import cPickle

class MTurk_Connection_Sim(MTurk_Connection):


    def __init__(self, experiment_id, job_id, model_file_name, vocabulary):

        print "Initializing Simulated Turk"
        sys.stdout.flush()

        self.job_id = job_id

        experiment = Experiment.objects.get(id=experiment_id)
        files_for_simulation = pickle.loads(experiment.files_for_simulation)

        self.modify_data = {}
        self.generate_data = []
        """
        generate_files = files_for_simulation[0]
        for generate_file in generate_files:
            with open(generate_file, 'r') as generate_file_handle:
                for line in generate_file_handle:
                    example = json.loads(line)
                    #print example
                    #sys.stdout.flush()
                    example = example['value'].split('\t')[0]
                    #print example
                    #sys.stdout.flush()
 
                    self.generate_data.append(example)
                    self.modify_data[example] = []
                    
        shuffle(self.generate_data)
        print self.generate_data[0:3]
        print "Done getting generate data ready."
        sys.stdout.flush()
        """
        modify_files = files_for_simulation[1]
        for modify_file in modify_files:
            with open(modify_file, 'r') as modify_file_handle:
                for line in modify_file_handle:
                    example = json.loads(line)
                    value = example['value'].split('\t')
                    sentence = value[0]
                    previous_sentence_not_example_of_event = value[1]
                    old_sentence = value[3]
                    if old_sentence not in self.modify_data:
                        self.modify_data[old_sentence] = []
                    self.modify_data[old_sentence].append(sentence)
        self.generate_data = self.modify_data.keys()
        shuffle(self.generate_data)

        print "Done getting generate and modify data ready"
        sys.stdout.flush()

        self.model_file_name = model_file_name
        self.model_meta_file_name = "{}.meta".format(model_file_name)
        self.vocabulary = vocabulary
        

    def delete_hits(self, task_id):
        #Delete all the fake tasks and answers we made
        print "Deleting simulated hits"
        sys.stdout.flush()


    def create_hits(self, category_id, task_id, num_hits):

        #No need to create any hits. Do the ones that were assigned to you.

        category_2_sentences = []
        category_2_worker_ids = []
        category_2_question_names = []
        
        for hit in range(num_hits):

            worker_id = str(uuid.uuid4())
            
            next_assignment_data = get_next_assignment(task_id, worker_id)
            next_assignment_question_data = next_assignment_data[
                'question_data'].split('\t')
            next_assignment_question_name = next_assignment_data[
                'question_name']


            if category_id == 0:
                generated_sentence = self.generate_data.pop()
                answer = (generated_sentence +
                          "\tTrigger\tPast\tFuture\tGeneral\tSimTaboo")
                submit_answer(task_id, worker_id,
                              next_assignment_question_name,
                              answer)
            elif category_id == 1:
                old_sentence = next_assignment_question_data[9]
                modified_sentence = self.modify_data[old_sentence].pop()
                answer = (modified_sentence + "\tNotPos\tHypOrGen\t" +
                          old_sentence + "\tSimTaboo")
                submit_answer(task_id, worker_id,
                              next_assignment_question_name,
                              answer)
            elif category_id == 2:

                sentence = next_assignment_question_data[10]
                category_2_sentences.append(sentence)
                category_2_worker_ids.append(worker_id)
                category_2_question_names.append(next_assignment_question_name)
                
        #For efficiency reasons, get the labels from NN in one batch.
        if category_id == 2:
            predicted_labels = test_cnn(category_2_sentences,
                                        [0 for s in category_2_sentences],
                                        self.model_file_name,
                                        self.vocabulary)
            for label, worker_id, question_name in zip(
                    predicted_labels,
                    category_2_worker_ids,
                    category_2_question_names):
                if label == 1:
                    answer = "Yes\tTrigger\tPast\tFuture\tGeneral\tHypothetical"
                else:
                    answer = "No\tFailing"
                    
                submit_answer(task_id, worker_id, question_name, answer)
                              

        #save the connection to the job for later use
        job = Job.objects.get(id=self.job_id)
        job.mturk_connection.replace(cPickle.dumps(self))
        job.save()
        
        return ['fakehitid' for i in range(num_hits)]