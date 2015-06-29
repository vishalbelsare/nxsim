import random
import networkx as nx
from .constants import *
from . import utils


class BaseAgent(object):
    #class variables, shared between all instances of this class
    r = random.Random(SEED)
    TIMESTEP_DEFAULT = 1.0

    def __init__(self, environment=None, agent_id=0, state=None, global_topology=None,
                 name='network_process', global_params=(), **state_params):
        """Base class for nxsim agents

        Parameters
        ----------
        environment : simpy.Environment() instance
            Simulation environment shared by processes
        agent_id : int or str
            Unique identifier
        state : object
            State of the Agent, this may be an integer or string or any other object
        global_topology : nx.Graph object
            Network topology of the simulation the agent belongs to

        name : str, optional
            Descriptive name of the agent
        global_params : dictionary-like, optional
            Key-value pairs of other global parameter to inject into the Agent
        state_params : keyword arguments, optional
            Key-value pairs of other state parameters for the agent
        """
        # Check for REQUIRED arguments
        assert environment is not None, TypeError('__init__ missing 1 required keyword argument: \'environment\'')
        assert agent_id is not None, TypeError('__init__ missing 1 required keyword argument: \'agent_id\'')
        assert len(state) != 0, TypeError('__init__ missing 1 required keyword argument: \'state\'')
        assert global_topology is not None, \
                TypeError('__init__ missing 1 required keyword argument: \'global_topology\'')

        # Initialize agent parameters
        self.id = agent_id
        self.state = state
        self.name = name
        self.state_params = state_params

        # Inject global parameters
        self.global_topology = global_topology
        self.global_params = global_params

        # Register agent to environment
        self.env = environment
        self.action = self.env.process(self.run())  # initialize every time an instance of the agent is created

    def run(self):
        """Subclass must specify a generator method!"""
        raise NotImplementedError()

    def get_all_nodes(self):
        """Returns list of nodes in the network"""
        return self.global_topology.nodes()

    def get_agents(self, state=None, limit_neighbors=False):
        """Returns list of agents based on their state and connectedness

        Parameters
        ----------
        state : int, str, or array-like, optional
            Used to select agents that have the same specified "state". If state = None, returns all agents regardless
            of its current state
        limit_neighbors : bool, optional
            Returns agents based on whether they are connected to this agent or not. If limit_neighbors = False,
            returns all agents whether or not it is directly connected to this agent
        """
        if limit_neighbors:
            agents = self.global_topology.neighbors(self.id)
        else:
            agents = self.get_all_nodes()

        if state is None:
            return [self.global_topology.node[_]['agent'] for _ in agents]  # return all regardless of state
        else:
            return [self.global_topology.node[_]['agent'] for _ in agents
                    if self.global_topology.node[_]['agent'].state == state]

    def get_all_agents(self, state=None):
        """Returns list of agents based only on their state"""
        return self.get_agents(state=state, limit_neighbors=False)

    def get_neighboring_agents(self, state=None):
        """Returns list of neighboring agents based on their state"""
        return self.get_agents(state=state, limit_neighbors=True)

    def get_neighboring_nodes(self):
        """Returns list of neighboring nodes"""
        return self.global_topology.neighbors(self.id)

    def get_agent(self, agent_id):
        """Returns agent with the specified id"""
        return self.global_topology.node[agent_id]['agent']

    def remove_node(self, agent_id):
        """Remove specified node from the network

        Parameters
        ----------
        agent_id : int
        """
        self.global_topology.remove_node(agent_id)

    def die(self):
        """Remove this node from the network"""
        self.remove_node(self.id)
    # def add_edge(self, node1, node2):
    #     self.global_topology.add_edge(self.id, self.current_supernode_id)
    #     self.log_topology_change(ADD_EDGE, node1, node2)
    #
    # def log_topology_change(self, action, node, node2=None):
    #     # Untested
    #     print(actions, node, node2)


class BaseNetworkAgent(BaseAgent):
    pass


class BaseEnvironmentAgent(BaseAgent):
    def __init__(self, simulation=None, name='environment_process', **state_params):
        """Base class for environment agents

        Parameters
        ----------
        simulation : NetworkSimulation class
        name : str, optional
            Descriptive name for the environment agent
        state_params : keyword arguments, optional
        """
        assert simulation is not None, TypeError('__init__ missing 1 required keyword argument: \'simulation\'')
        self.sim = simulation

        super().__init__(environment=self.sim.env, agent_id=-1, state='environment_agent',
                         global_topology=self.sim.G, name=name, global_params=self.sim.global_params, **state_params)

    def add_node(self, agent_type=None, state=None, name='network_process', **state_params):
        """Add a new node to the current network

        Parameters
        ----------
        agent_type : NetworkAgent subclass
            Agent in the new node will be instantiated using this agent class
        state : object
            State of the Agent, this may be an integer or string or any other
        name : str, optional
            Descriptive name of the agent
        state_params : keyword arguments, optional
            Key-value pairs of other state parameters for the agent

        Return
        ------
        int
            Agent ID of the new node
        """
        agent_id = int(self.sim.id_counter)
        agent = agent_type(self.sim.env, agent_id=agent_id, state=state, global_topology=self.sim.G,
                           name=name, global_params=self.sim.global_params, **state_params)
        self.sim.G.add_node(self.sim.id_counter, {'agent': agent})
        self.sim.id_counter +=  1
        return agent_id


    def add_edge(self, agent_id1, agent_id2, edge_attr_dict=None, *edge_attrs):
        """
        Add an edge between agent_id1 and agent_id2. agent_id1 and agent_id2 correspond to Networkx node IDs.

        This is a wrapper for the Networkx.Graph method `.add_edge`.

        Agents agent_id1 and agent_id2 will be automatically added if they are not already present in the graph.
        Edge attributes can be specified using keywords or passing a dictionary with key-value pairs

        Parameters
        ----------
        agent_id1, agent_id2 : nodes
            Nodes (as defined by Networkx) can be any hashable type except NoneType
        edge_attr_dict : dictionary, optional (default = no attributes)
            Dictionary of edge attributes. Assigns values to specified keyword attributes and overwrites them if already
            present.
        edge_attrs : keyword arguments, optional
            Edge attributes such as labels can be assigned directly using keyowrd arguments
        """
        if agent_id1 in self.global_topology.nodes(data=False):
            if agent_id2 in self.global_topology.nodes(data=False):
                self.global_topology.add_edge(agent_id1, agent_id2, edge_attr_dict=edge_attr_dict, *edge_attrs)
            else:
                raise ValueError('\'agent_id2\'[{}] not in list of existing agents in the network'.format(agent_id2))
        else:
            raise ValueError('\'agent_id1\'[{}] not in list of existing agents in the network'.format(agent_id1))

    def log_topology(self):
        return NotImplementedError()


class LoggingAgent(object):
    def __init__(self, simulation=None, dir_path='sim_01', logging_interval=1):
        """Log states of agents and graph topology

        Parameters
        ----------
        simulation : NetworkSimulation instance
        dir_path : directory path, str, optional (default = 'sim_01')
        logging_interval : int, optional (default = 1)
        """
        self.sim = simulation
        self.dir_path = dir_path
        self.interval = logging_interval

        self.state_tuples = list()
        self.state_vector_tuples = list()
        self.topology_tuples = list()

        # Initialize process
        self.env = self.sim.env
        self.action = self.env.process(self.run())

        # Initialize empty graph
        self.topology = nx.Graph()

    def run(self):
        while True:
            self.log_current_state()
            yield self.env.timeout(self.interval)

    def log_current_state(self):
        nodes = self.sim.G.nodes(data=True)
        states = [node[1]['agent'].state for node in nodes]

        # log states
        self.state_tuples.append(StateTuple(time=self.env.now, states=states))

        # log topology ONLY IF it changed
        if not nx.fast_could_be_isomorphic(self.topology, nx.Graph(self.sim.G)):
            self.topology = utils.create_copy_without_data(self.sim.G)
            self.topology_tuples.append(TopologyTuple(time=self.env.now(), topology=self.topology))

    def log_trial_to_files(self, trial_id=None):
        assert trial_id is not None, TypeError('missing 1 required keyword argument: \'trial_id\'. '
                                               'Cannot be set to NoneType')
        utils.log_all_to_file(states=self.state_tuples, dir_path=self.dir_path, trial_id=trial_id)