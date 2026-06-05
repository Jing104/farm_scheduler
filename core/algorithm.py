import math
import random

class HeavySchedulerAlgorithm:
    """
    无人农机多目标动态调度与路径规划核心引擎
    """
    def __init__(self):
        pass

    @staticmethod
    def calculate_distance(p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def optimize_scheduling(self, machinery_list, task_list):
        """
        输入当前空闲农机及待作业地块，计算最优匹配矩阵与冲突规避路径
        machinery_list: [{'id': 1, 'pos': (x,y), 'type': 'harvester', 'fuel': 80}]
        task_list: [{'id': 101, 'pos': (x,y), 'area': 50, 'priority': 2}]
        """
        if not machinery_list or not task_list:
            return {}

        allocation_map = {}
        available_machinery = machinery_list.copy()

        # 按优先级降序排列任务
        sorted_tasks = sorted(task_list, key=lambda x: x.get('priority', 0), reverse=True)

        for task in sorted_tasks:
            if not available_machinery:
                break
            
            best_candidate = None
            min_cost = float('inf')
            
            for machinery in available_machinery:
                dist = self.calculate_distance(machinery['pos'], task['pos'])
                # 代价函数: 距离 * 1.5 - 残余油量权重 + 面积惩罚
                cost = dist * 1.5 - (machinery['fuel'] * 0.2) + (task['area'] * 0.1)
                
                if cost < min_cost:
                    min_cost = cost
                    best_candidate = machinery

            if best_candidate:
                allocation_map[task['id']] = {
                    'machinery_id': best_candidate['id'],
                    'cost': round(min_cost, 2),
                    'estimated_time': round(dist / 5.0, 1), # 假设基准航速 5m/s
                    'planned_path': [best_candidate['pos'], task['pos']]
                }
                available_machinery.remove(best_candidate)

        return allocation_map