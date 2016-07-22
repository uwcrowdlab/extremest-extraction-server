from flask.ext.restful import reqparse, abort, Api, Resource
from flask import url_for, redirect, render_template
import json
import string
import pickle
from app import app
from train import gather, restart, gather_status, retrain
import sys
import uuid
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

pause_parser = reqparse.RequestParser()
pause_parser.add_argument('job_id', type=str, required=True)

job_status_parser = reqparse.RequestParser()
job_status_parser.add_argument('job_id', type=str, required=True)


gather_status_parser = reqparse.RequestParser()
gather_status_parser.add_argument('job_id', type=str, required=True)
gather_status_parser.add_argument('positive_types', required=True,
                                  action='append')

retrain_parser = reqparse.RequestParser()
retrain_parser.add_argument('job_id', type=str, required=True)
retrain_parser.add_argument('positive_types', required=True,
                            action='append')

retrain_status_parser = reqparse.RequestParser()
retrain_status_parser.add_argument('job_id', type=str, required=True)


class GatherExtractorApi(Resource):
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
                  num_training_examples_in_model = -1,
                  current_hit_ids = [],
                  checkpoints = {},
                  status = 'Running')
        job.save()
        job_id = str(job.id)
        
        gather.delay(task_information, budget, job_id)
            
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
    def get(self):
        args = restart_parser.parse_args()
        job_id = args['job_id']

        job = Job.objects.get(id = job_id)
        job.status = 'Running'
        job.save()

        print "Job %s restarted" % job_id
        
        return 1

class PauseApi(Resource):
    def get(self):
        args = pause_parser.parse_args()
        job_id = args['job_id']

        job = Job.objects.get(id = job_id)
        job.status = 'Paused'
        job.save()

        print "Job %s paused" % job_id
        return 1

class JobStatusApi(Resource):
    def get(self):
        args = job_status_parser.parse_args()
        job_id = args['job_id']

        job = Job.objects.get(id = job_id)

        try:
            return job.status
        except AttributeError:
            job.status = 'Paused'
            job.save()
            return job.status

        
class GatherStatusApi(Resource):
    def get(self):
        args = gather_status_parser.parse_args()
        job_id = args['job_id']
        positive_types = args['positive_types']

        print "POSITIVE TYPES"
        print positive_types
        return gather_status(job_id, positive_types)            


class RetrainExtractorApi(Resource):
    def get(self):
        args = retrain_parser.parse_args()
        job_id = args['job_id']
        positive_types = args['positive_types']
        
        job = Job.objects.get(id = job_id)
        job.num_training_examples_in_model = -1
        job.save()
        
        retrain.delay(job_id, positive_types)
        return True


class RetrainStatusApi(Resource):
    def get(self):
        args = retrain_status_parser.parse_args()
        job_id = args['job_id']

        job = Job.objects.get(id=job_id)
        return job.num_training_examples_in_model



