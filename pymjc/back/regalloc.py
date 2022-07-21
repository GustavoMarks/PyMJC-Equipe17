from __future__ import annotations
from abc import abstractmethod
import sys
from typing import Set
from pymjc.back import assem, flowgraph, graph
from pymjc.front import frame, temp


class RegAlloc (temp.TempMap):
    def __init__(self, frame: frame.Frame, instr_list: assem.InstrList):
        self.frame: frame.Frame = frame
        self.instrs: assem.InstrList = instr_list
        #TODO

        while True:
            
            self.liveness_analysis()

            # Java Init: 
            # Nós gerais
            self.pre_colored_nodes = []
            self.normal_colored_nodes = {}
            # Nós separados por etapas
            self.initial_nodes = []
            self.spill_nodes = {}
            self.coalesce_nodes = {}
            # Pilha de nós para coloração
            self.node_stack = []
            # WorkLists
            self.simplify_worklist = {}
            self.freeze_worklist = {}
            self.spill_worklist = {}
            # Nós move
            self.coalesce_move_nodes = {}
            self.constrain_move_nodes = {}
            self.freeze_move_nodes = {}
            self.active_move_nodes = {}
            # Para decidir se vai ter um custo personalizado de spill
            self.spill_cost = {}
            # Propriedades referentes à adjacencia
            self.adjacence_sets = {}
            self.adjacence_list = {}
            # Moves
            self.move_nodes_list = {}
            # Tabelas de referência a características dos nós(alias, color e degree)
            self.node_alias_table = {}
            self.node_color_table = {}
            self.node_degree_table = {}

            # Criando lista de registradores para temp pré-coloridos
            for counter in range(len(self.frame.registers())):
                inst_temp: temp.Temp = self.frame.registers()[counter]
                node: graph.Node = self.liveness_output.tnode(inst_temp)

                self.pre_colored_nodes.append(node)
                self.spill_cost[node.to_string()] = sys.maxsize

                self.node_color_table[node.to_string()] = node
                self.node_degree_table[node.to_string()] = 0

            # Criando lista de registradores para temp não pré-coloridos
            node_list = self.liveness_output.nodes()
            while node_list != None:
                node: graph.Node = node_list.head

                if not node in self.pre_colored_nodes:
                    self.initial_nodes.append(node)
                    self.spill_cost[node.to_string()] = 1

                    self.node_degree_table[node.to_string()] = 0
                
                node_list = node_list.tail


            self.build()
            self.make_worklist()

            while True:
                if len(list(self.simplify_worklist.values())) != 0:
                    self.simplify()
                elif len(list(self.worklist_move_nodes.values())) != 0:
                    self.coalesce()
                elif len(list(self.freeze_worklist.values())) != 0:
                    self.freeze()
                elif len(list(self.spill_worklist.values())) != 0:
                    self.select_spill()

                if not (len(list(self.spill_worklist.values())) != 0 or 
                len(list(self.freeze_worklist.values())) != 0 or
                len(list(self.worklist_move_nodes.values())) != 0 or
                len(list(self.simplify_worklist.values())) != 0):
                    break
            
            self.assing_colors()

            if len(list(self.spill_nodes.values())) != 0:
                self.rewrite_program()
                break


    def liveness_analysis(self) -> None:
        # Java: LivenessAnalysis
        self.assem_flow_graph = flowgraph.AssemFlowGraph(self.instrs)
        self.liveness_output = Liveness(self.assem_flow_graph)

    def build(self) -> None:
        pass

    def make_worklist(self) -> None:
        pass

    def simplify(self) -> None:
        pass

    def coalesce(self) -> None:
        pass

    def freeze(self) -> None:
        pass

    def select_spill(self) -> None:
        pass

    def assing_colors(self) -> None:
        pass
        
    def rewrite_program(self) -> None:
        pass

    def temp_map(self, temp: temp.Temp) -> str:
        #TODO
        return temp.to_string()
    

class Color(temp.TempMap):
    def __init__(self, ig: InterferenceGraph, initial: temp.TempMap, registers: temp.TempList):
        #TODO
        pass
    
    def spills(self) -> temp.TempList:
        #TODO
        return None

    def temp_map(self, temp: temp.Temp) -> str:
        #TODO
        return temp.to_string()

class InterferenceGraph(graph.Graph):
    
    @abstractmethod
    def tnode(self, temp:temp.Temp) -> graph.Node:
        pass

    @abstractmethod
    def gtemp(self, node: graph.Node) -> temp.Temp:
        pass

    @abstractmethod
    def moves(self) -> MoveList:
        pass
    
    def spill_cost(self, node: graph.Node) -> int:
      return 1


class Liveness (InterferenceGraph):

    def __init__(self, flow: flowgraph.FlowGraph):
        self.live_map = {}
        
        #Flow Graph
        self.flowgraph: flowgraph.FlowGraph = flow
        
        #IN, OUT, GEN, and KILL map tables
        #The table maps complies with: <Node, Set[Temp]>
        self.in_node_table = {}
        self.out_node_table = {}
        self.gen_node_table = {}
        self.kill_node_table = {}

        #Util map tables
        #<Node, Temp>
        self.rev_node_table = {}
        #<Temp, Node>
        self.map_node_table = {}
        
        #Move list
        self.move_list: MoveList = None

        self.build_gen_and_kill()
        self.build_in_and_out()
        self.build_interference_graph()
    
    def add_ndge(self, source_node: graph.Node, destiny_node: graph.Node):
        if (source_node is not destiny_node and not destiny_node.comes_from(source_node) and not source_node.comes_from(destiny_node)):
            super.add_edge(source_node, destiny_node)

    def show(self, out_path: str) -> None:
        if out_path is not None:
            sys.stdout = open(out_path, 'w')   
        node_list: graph.NodeList = self.nodes()
        while(node_list is not None):
            temp: temp.Temp = self.rev_node_table.get(node_list.head)
            print(temp + ": [ ")
            adjs: graph.NodeList = node_list.head.adj()
            while(adjs is not None):
                print(self.rev_node_table.get(adjs.head) + " ")
                adjs = adjs.tail

            print("]")
            node_list = node_list.tail
    
    def get_node(self, temp: temp.Temp) -> graph.Node:
      requested_node: graph.Node = self.map_node_table.get(temp)
      if (requested_node is None):
          requested_node = self.new_node()
          self.map_node_table[temp] = requested_node
          self.rev_node_table[requested_node] = temp

      return requested_node

    def node_handler(self, node: graph.Node):
        def_temp_list: temp.TempList = self.flowgraph.deff(node)
        while(def_temp_list is not None):
            got_node: graph.Node  = self.get_node(def_temp_list.head)

            for live_out in self.out_node_table.get(node):
                current_live_out = self.get_node(live_out)
                self.add_edge(got_node, current_live_out)

            def_temp_list = def_temp_list.tail

  
    def move_handler(self, node: graph.Node):
        source_node: graph.Node  = self.get_node(self.flowgraph.use(node).head)
        destiny_node: graph.Node = self.get_node(self.flowgraph.deff(node).head)

        self.move_list = MoveList(source_node, destiny_node, self.move_list)
    
        for temp in self.out_node_table.get(node):
            got_node: graph.Node = self.get_node(temp)
            if (got_node is not source_node ):
                self.addEdge(destiny_node, got_node)


    def out(self, node: graph.Node) -> Set[temp.Temp]:
        temp_set = self.out_node_table.get(node)
        return temp_set


    def tnode(self, temp:temp.Temp) -> graph.Node:
        node: graph.Node = self.map_node_table.get(temp)
        if (node is None ):
            node = self.new_node()
            self.map_node_table[temp] = node
            self.rev_node_table[node] = temp
        
        return node

    def gtemp(self, node: graph.Node) -> temp.Temp:
        temp: temp.Temp = self.rev_node_table.get(node)
        return temp

    def moves(self) -> MoveList:
        return self.move_list

    def build_gen_and_kill(self):
        #TODO
        pass

    def build_in_and_out(self):
        #TODO
        # for each n
        #     in[n] ← {}; out[n] ← {}
        # repeat
        #     for each n
        #         in'[n] ← in[n]; out'[n] ← out[n]
        #         in[n] ← use[n] ∪ (out[n] − def[n])
        #         out[n] ← Us∈succ[n] in[s]
        # until in[n] = in[n] and out[n] = out[n] for all n

        node_list: graph.NodeList = self.flowgraph.mynodes

        while node_list.head != None:
            self.in_node_table[node_list.head.to_string()] = {}
            self.out_node_table[node_list.head.to_string()] = {}
            node_list = node_list.tail

        in_node_table__ = {}
        out_node_table__ = {}
       
        while True:
            node_list: graph.NodeList = self.nodes()
            while node_list != None:
                in_n: Set = self.in_node_table.get(node_list.head)
                out_n: Set = self.out(node_list.head)

                in_node_table__[node_list.head.to_string()] = in_n
                out_node_table__[node_list.head.to_string()] = out_n

                use_n: Set = self.flowgraph.use(node_list.head)
                def_n: Set = self.flowgraph.deff(node_list.head)

                union_in_set = use_n.union(out_n.difference(def_n))
                self.in_node_table[node_list.head.to_string()] = union_in_set

                succ: Set = node_list.head.succ()
                for s in succ:
                    out_n.union(s)

                self.out_node_table[node_list.head.to_string()] = out_n

                node_list = node_list.tail
          
            if in_node_table__.values() == self.in_node_table.values() and out_node_table__.values() == self.out_node_table.values():
              break

        pass

    def build_interference_graph(self):
        #TODO
        node_list: graph.NodeList = self.flowgraph.mynodes

        while node_list != None:
            if self.flowgraph.is_move(node_list.head):
                self.move_handler(node_list.head)
            else:
                self.node_handler(node_list.head)
            
            node_list = node_list.tail
            
        pass

class Edge():

    edges_table = {}

    def __init__(self):
        super.__init__()
    
    def get_edge(self, origin_node: graph.Node, destiny_node: graph.Node) -> Edge:
        
        origin_table = Edge.edges_table.get(origin_node)
        destiny_table = Edge.edges_table.get(destiny_node)
        
        if (origin_table is None):
            origin_table = {}
            Edge.edges_table[origin_node] = origin_table

        if (destiny_table is None):
            destiny_table = {}
            Edge.edges_table[destiny_node] = destiny_table
        
        requested_edge: Edge  = origin_table.get(destiny_node)

        if(requested_edge is None):
            requested_edge = Edge()
            origin_table[destiny_node] = requested_edge
            destiny_table[origin_node] = requested_edge

        return requested_edge



class MoveList():

   def __init__(self, s: graph.Node, d: graph.Node, t: MoveList):
      self.src: graph.Node = s
      self.dst: graph.Node = d
      self.tail: MoveList = t
