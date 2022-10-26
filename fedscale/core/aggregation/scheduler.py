import pickle

from concurrent import futures
from fedscale.core.channels.channel_context import ClientConnections
import fedscale.core.channels.job_api_pb2_grpc as job_api_pb2_grpc
from fedscale.core.channels import job_api_pb2
import fedscale.core.logger.aggragation as logger
import fedscale.core.config_parser as parser
from fedscale.core import commons
from fedscale.core.fllibs import *

import grpc

MAX_MESSAGE_LENGTH = 1*1024*1024*1024  # 1GB

class Scheduler(job_api_pb2_grpc.JobServiceServicer):
    def __init__(self, args):
        logger.initiate_aggregator_setting()
        logging.info(f"Job args {args}")

        self.args = args
        self.grpc_server = None
        self.aggregators = {}
        self.aggr_counter = 0
        self.register_lock = threading.Lock()

    def init_control_communication(self, args):
        # initiate server
        self.grpc_server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=20),
            options=[
                ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
                ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
            ],
        )
        job_api_pb2_grpc.add_JobServiceServicer_to_server(
            self, self.grpc_server)
        port = '[::]:{}'.format(self.args.scheduler_port)

        logging.info(f'%%%%%%%%%% Opening scheduler sever using port {port} %%%%%%%%%%')

        self.grpc_server.add_insecure_port(port)
        self.grpc_server.start()
    
    def AGGREGATOR_REGISTER(self, request, context):
        # There won't be a large number of aggregators
        # so register immediately
        aggr_ip = request.aggregator_ip
        aggr_port = request.aggregator_port
        aggr_info = self.deserialize_response(request.aggregator_info)

        self.register_lock.acquire()
        aggr_communicator = ClientConnections(aggr_ip, aggr_port)
        aggr_id = str(self.aggr_counter)
        self.aggr_counter += 1
        self.aggregators[aggr_id] = {
            'load': 0,
            'capacity': aggr_info['capacity'],
            'communicator': aggr_communicator
        }
        logging.info(f"Aggregator {aggr_id} registered, address {aggr_ip}:{aggr_port}.")
        self.register_lock.release()

        dummy_meta = self.serialize_response(commons.DUMMY_RESPONSE)
        data = self.serialize_response({'aggregator_id': aggr_id})
        return job_api_pb2.ServerResponse(event=commons.DUMMY_EVENT,
                                          meta=dummy_meta, data=data)
    
    def AGGREGATOR_ADJUST(self, request, context):
        raise NotImplementedError('Method not implemented!')
    
    def AGGREGATOR_WEIGHT_STREAM(self, request, context):
        # directly relay
        pass

    def deserialize_response(self, responses):
        return pickle.loads(responses)

    def serialize_response(self, responses):
        return pickle.dumps(responses)
    
    def event_monitor(self):
        print("Hi I'm running!")
        while(True):
            pass

    def run(self):
        self.init_control_communication()
        self.event_monitor()

    