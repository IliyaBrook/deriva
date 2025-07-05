import random
import operator
from typing import List, Dict, Any, Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class State(TypedDict):
    length: int
    numbers: List[int]
    squared_results: Annotated[List[int], operator.add]
    sum_of_squares: int


class MapperState(TypedDict):
    number: int
    squared_results: Annotated[List[int], operator.add]


def generator_node(state: State) -> Dict[str, Any]:
    length = state["length"]
    
    numbers = [random.randint(0, 99) for _ in range(length)]
    
    return {
        "numbers": numbers,
        "squared_results": []
    }


def mapper_node(state: MapperState) -> Dict[str, Any]:
    number = state["number"]
    squared = number * number
    
    return {
        "squared_results": [squared]
    }


def reducer_node(state: State) -> Dict[str, Any]:
    squared_results = state["squared_results"]
    sum_of_squares = sum(squared_results)
    
    return {
        "sum_of_squares": sum_of_squares
    }


def assign_mappers(state: State) -> List[Send]:
    numbers = state["numbers"]
    
    return [Send("mapper", {"number": num}) for num in numbers]


def create_sum_of_squares_graph():
    builder = StateGraph(State)
    
    builder.add_node("generator", generator_node)
    builder.add_node("mapper", mapper_node)
    builder.add_node("reducer", reducer_node)
    
    builder.add_edge(START, "generator")
    
    builder.add_conditional_edges("generator", assign_mappers)
    
    builder.add_edge("mapper", "reducer")
    
    builder.add_edge("reducer", END)
    
    graph = builder.compile()
    
    return graph


if __name__ == "__main__":
    graph = create_sum_of_squares_graph()
    
    test_input = {"length": 5}
    result = graph.invoke(test_input)
    
    print(f"Input: {test_input}")
    print(f"Generated numbers: {result['numbers']}")
    print(f"Squared results: {result['squared_results']}")
    print(f"Sum of squares: {result['sum_of_squares']}")
    
    manual_check = sum(num ** 2 for num in result['numbers'])
    print(f"Manual verification: {manual_check}")
    print(f"Results match: {result['sum_of_squares'] == manual_check}") 