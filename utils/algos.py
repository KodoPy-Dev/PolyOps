########################•########################
"""                   KodoPy                  """
########################•########################

from collections import deque


def index_wrap(index:int, sequence:list):
    return index % len(sequence)


def wrap_to_next(item=None, sequence=[]):
    if item in sequence:
        index = sequence.index(item) + 1
        return sequence[index % len(sequence)]
    return item


def sections_from_list(items, split_points):
    '''Returns a list of list or None
    Splits the items into sub list based on split points
    Each sub list will contain the split point on the start and end
    '''
    if not items or not split_points: return None

    start = None
    for index, item in enumerate(items):
        if item in split_points:
            start = index
            break
    end = None
    for index, item in enumerate( reversed(items)):
        if item in split_points:
            end = len(items) - index
            break

    if start is None or end is None: return None

    sections = []
    sub_items = []
    
    sub_items = items[end-1:]
    for item in items:
        sub_items.append(item)
        if item in split_points:
            sections.append(sub_items)
            sub_items = []
            break

    split_count = 0

    for item in items[start:end]:
        sub_items.append(item)
        if item in split_points:
            split_count += 1
        if split_count == 2:
            split_count = 1
            sections.append(sub_items)
            sub_items = []
            sub_items.append(item)

    return sections


def bfs(graph, start):
    visited = set()
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node not in visited:
            visited.add(node)
            queue.extend(graph[node] - visited)


def dfs(graph, start, visited=None):
    if visited is None:
        visited = set()
    visited.add(start)
    
    for neighbor in graph[start] - visited:
        dfs(graph, neighbor, visited)


def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
