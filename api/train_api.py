from flask.ext.restful import reqparse, abort, Api, Resource
from flask import url_for, redirect, render_template
import json
import string
import pickle
from app import app
from train import train, restart, gather_status, retrain
import sys
import uuid
import redis
from schema.job import Job

train_parser = reqparse.RequestParser()
train_parser.add_argument('event_name', type=str, required=True)
train_parser.add_argument('event_definition', type=str, required=True)
train_parser.add_argument('event_pos_example_1', type=str, required=True)
train_parser.add_argument('event_pos_example_1_trigger',
                          type=str, required=True)
train_parser.add_argument('event_pos_example_2', type=str, required=True)
train_parser.add_argument('event_pos_example_2_trigger',
                          type=str, required=True)
train_parser.add_argument('event_pos_example_nearmiss', type=str, required=True)
train_parser.add_argument('event_neg_example',
                          type=str, required=True)
train_parser.add_argument('event_neg_example_nearmiss',
                          type=str, required=True)

#train_parser.add_argument('task_information', type=str, required=True)
train_parser.add_argument('budget', type=str, required=True)

restart_parser = reqparse.RequestParser()
restart_parser.add_argument('job_id', type=str, required=True)


gather_status_parser = reqparse.RequestParser()
gather_status_parser.add_argument('job_id', type=str, required=True)

retrain_parser = reqparse.RequestParser()
retrain_parser.add_argument('job_id', type=str, required=True)

retrain_status_parser = reqparse.RequestParser()
retrain_status_parser.add_argument('job_id', type=str, required=True)


class TrainExtractorApi(Resource):
    def post(self):
        args = train_parser.parse_args()
        event_name = args['event_name']
        event_definition = args['event_definition']
        event_pos_example_1 = args['event_pos_example_1']
        event_pos_example_1_trigger = args['event_pos_example_1_trigger']
        event_pos_example_2 = args['event_pos_example_2']
        event_pos_example_2_trigger = args['event_pos_example_2_trigger']
        event_pos_example_nearmiss = args['event_pos_example_nearmiss']
        
        event_neg_example = args['event_neg_example']
        event_neg_example_nearmiss = args['event_neg_example_nearmiss']


        task_information = (event_name, event_definition,
                            event_pos_example_1,
                            event_pos_example_1_trigger,
                            event_pos_example_2,
                            event_pos_example_2_trigger,
                            event_pos_example_nearmiss,
                            event_neg_example,
                            event_neg_example_nearmiss)
        
        #task_information = args['task_information']
        budget = int(args['budget'])

        #Generate a random job_id
        job = Job(task_information = pickle.dumps((task_information, budget)),
                  model = 'None',
                  model_meta = 'None',
                  vocabulary = 'None',
                  num_training_examples_in_model = -1,
                  checkpoints = {})
        job.save()
        job_id = str(job.id)
        
        train.delay(task_information, budget, app.config, job_id)
            
        return redirect(url_for(
            'status',  
            event_name = event_name,
            event_definition = event_definition,
            event_pos_example_1 = event_pos_example_1,
            event_pos_example_1_trigger = event_pos_example_1_trigger,
            event_pos_example_2 = event_pos_example_2,
            event_pos_example_2_trigger = event_pos_example_2_trigger,
            event_pos_example_nearmiss = event_pos_example_nearmiss,
            event_neg_example = event_neg_example,
            event_neg_example_nearmiss = event_neg_example_nearmiss,
            job_id = job_id))


class RestartApi(Resource):
    def post(self):
        args = restart_parser.parse_args()
        job_id = args['job_id']
        
        restart.delay(job_id, app.config)
            
        return True

    
class GatherStatusApi(Resource):
    def get(self):
        args = gather_status_parser.parse_args()
        job_id = args['job_id']

        return gather_status(job_id, app.config)            


class RetrainExtractorApi(Resource):
    def get(self):
        args = retrain_parser.parse_args()
        job_id = args['job_id']

        job = Job.objects.get(id = job_id)
        job.model = 'None'
        job.model_meta = 'None'
        job.vocabulary = 'None'
        job.num_training_examples_in_model = -1
        job.save()
        
        #app.redis.hset(job_id, 'model_meta', 'None')
        #app.redis.hset(job_id, 'model', 'None')

        retrain.delay(job_id, app.config)            

        return True


class RetrainStatusApi(Resource):
    def get(self):
        args = retrain_status_parser.parse_args()
        job_id = args['job_id']

        #model_file_name = app.redis.hmget(job_id, 'model_meta')[0]
        job = Job.objects.get(id=job_id)
        return job.num_training_examples_in_model
