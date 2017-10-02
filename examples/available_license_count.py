#! /usr/bin/env python

__author__ = 'Todd Radel <tradel@appdynamics.com> & Toby Davies <toby.davies@appdynamics.com>'

import itertools

from datetime import datetime
from appd.cmdline import parse_argv
from appd.request import AppDynamicsClient
from time import mktime

def incr(d, name, amt=1):
    d[name] = d.get(name, 0) + amt


args = parse_argv()
c = AppDynamicsClient(args.url, args.username, args.password, args.account, args.verbose)

time_in_mins = 24 * 60
end_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
end_epoch = int(mktime(end_time.timetuple())) * 1000

nodes = []
for app in c.get_applications():
    for tier in c.get_tiers(app.id):
        for node in c.get_nodes(app.id, tier.id):
            av = c.get_metrics('Application Infrastructure Performance|'+tier.name+'|Individual Nodes|'+node.name+'|Agent|App|Availability', app.id, time_range_type='BEFORE_TIME', end_time=end_epoch, duration_in_mins=50, rollup=False)


            # node_type = node.type
            # print node.id, node.machine_id, node.machine_name, node.type
            if (node.has_machine_agent or node.has_app_agent):
                if node.has_app_agent:
                    if 'PHP' in node.type:
                        node.group_type = 'PHP App Agent'
                    if 'IIS' in node.type:
                        node.group_type = '.NET App Agent'
                    else:
                        node.group_type = 'Java App Agent'
                else:
                    node.group_type = 'Machine Agent only'
                if len(av[0].values) > 0 and av[0].values[0].current == 1:
                    node.reporting = 1
                else:
                    node.reporting = 0
                nodes.append(node)


# Sort and group the nodes by machine_id.

group_func = lambda x: x.machine_id
nodes.sort(key=group_func)

host_counts = dict()
node_counts = dict()
lic_counts = dict()
for machine_id, nodes_on_machine_iter in itertools.groupby(nodes, key=group_func):

    nodes_on_machine = list(nodes_on_machine_iter)
    first_node = nodes_on_machine[0]
    agent_type = first_node.group_type
    types = [x.group_type for x in nodes_on_machine]
    all_same = all(x.group_type == agent_type for x in nodes_on_machine)
    # print all_same, types
    assert all_same, first_node


    incr(node_counts, agent_type, len(nodes_on_machine))

    active_nodes = [node for node in nodes_on_machine if node.reporting==1]

    license_count = 0
    if len(active_nodes) > 0:
        license_count = 1
    if 'Java' in agent_type:
        license_count = len(active_nodes)

    incr(lic_counts, agent_type, license_count)
    incr(host_counts, agent_type, 1)

    # if '.NET' in agent_type:
    #     node_names = [x.name for x in nodes_on_machine]
    #     print 'Host:', first_node.machine_name, '\n\t', '\n\t'.join(node_names)


# Print the results.
tot_nodes, tot_hosts, tot_licenses = (0, 0, 0)
header_fmt = '%-30s %-15s %-15s %s'
data_fmt = '%-30s %15d %15d %15d'

print
print 'License usage report for ', args.url
print 'Generated at: ', datetime.now()
print
print header_fmt % ('Node Type', 'Node Count', 'Host Count', 'License Count')
print header_fmt % ('=' * 30, '=' * 15, '=' * 15, '=' * 15)

for node_type in ('Java App Agent', '.NET App Agent', 'PHP App Agent', 'Machine Agent only'):
    node_count = node_counts.get(node_type, 0)
    host_count = host_counts.get(node_type, 0)
    lic_count = lic_counts.get(node_type, 0)
    tot_nodes += node_count
    tot_hosts += host_count
    tot_licenses += lic_count
    print data_fmt % (node_type, node_count, host_count, lic_count)

print header_fmt % ('=' * 30, '=' * 15, '=' * 15, '=' * 15)
print data_fmt % ('TOTAL', tot_nodes, tot_hosts, tot_licenses)
