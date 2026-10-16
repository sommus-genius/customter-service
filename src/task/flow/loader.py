from pathlib import Path

import yaml

from task.flow.flows import FlowList, Flow, FlowSlot


class FlowLoader:
    def load_many(self, paths: list[Path]) -> FlowList:
        """
        加载多个 yml 文件
        :param paths:
        :return:
        """
        flows: list[Flow] = []
        slots: dict[str, FlowSlot] = {}

        for path in paths:
            # 1.加载一个 yml 文件
            single_flow_list = self.load(path)

            # 2.获取每个文件的flow并且合并到最终的flows中
            flows.extend(single_flow_list.flows)

            # 3.获取每个文件的slot，并将其合并、去重
            sub_slots = single_flow_list.slots
            # 两个集合取交集，判断是否重复
            duplicate_slot_name = set(slots).intersection(sub_slots)
            if duplicate_slot_name:
                raise ValueError(f"Duplicate slot name: {duplicate_slot_name}")
            slots.update(sub_slots)

        return FlowList(flows=flows, slots=slots)

    def load(self, path: Path) -> FlowList:
        # 1. 读取 yml
        with open(path, 'r', encoding='utf-8') as f:
            # 防止脚本注入
            data = yaml.safe_load(f)

        # 2. 加载 slots
        slots = self._load_slots(data.get('slots', {}))

        # 3. 加载 flows
        flows = self._load_flows(data.get('flows', {}), slots)

        # 4. 返回 FlowList
        return FlowList(flows=flows, slots=slots)

    def _load_slots(self, yml_slots_data: dict) -> dict[str, FlowSlot]:
        slots: dict[str, FlowSlot] = {}

        for slot_name, slot_data in yml_slots_data.items():
            if slot_data is None:
                slot_data = {}

            slots[slot_name] = FlowSlot(name=slot_name, **slot_data)

        return slots

    def _load_flows(self, flows_data, slots: dict[str, FlowSlot]) -> list[Flow]:
        flows: list[Flow] = []

        if not isinstance(flows_data, dict):
            # 兼容 flows 是 list 的情况
            if isinstance(flows_data, list):
                for flow_data in flows_data:
                    if not isinstance(flow_data, dict):
                        continue
                    # 把 slots dict 转成 list 再传
                    flow_data_copy = self._normalize_flow_data(flow_data)
                    flow_data_copy['slots'] = list(slots.values())
                    flow = Flow(**flow_data_copy)
                    flows.append(flow)
            return flows

        # flows 是 dict：key 是 flow id，value 是 flow 配置
        for flow_id, flow_data in flows_data.items():
            if not isinstance(flow_data, dict):
                continue

            # 把 YAML 数据规范化：next 字符串转 list，slots dict 转 list
            normalized = self._normalize_flow_data(flow_data)

            # 把 dict key 作为 id 注入
            normalized['id'] = flow_id

            # slots 字段：dict -> list
            normalized['slots'] = list(slots.values())

            flow = Flow(**normalized)
            flows.append(flow)

        return flows

    @staticmethod
    def _normalize_flow_data(flow_data: dict) -> dict:
        """规范化 flow 数据：处理 next 字段和 steps 中的类型转换"""
        result = dict(flow_data)

        # 处理 steps 中的 next 字段：字符串 -> list
        if 'steps' in result and isinstance(result['steps'], list):
            for step in result['steps']:
                if isinstance(step, dict) and 'next' in step and isinstance(step['next'], str):
                    step['next'] = [step['next']]

        return result


if __name__ == '__main__':
    base_path = Path(__file__).parents[3]
    user_flow_path = base_path / "flow_config" / "user_flows.yml"
    system_flow_path = base_path / "flow_config" / "system_flows.yml"

    loader = FlowLoader()
    flow_list = loader.load_many([user_flow_path, system_flow_path])

    print(flow_list)