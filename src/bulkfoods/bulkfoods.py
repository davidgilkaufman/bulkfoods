from collections import namedtuple
from functools import reduce
from fractions import Fraction
from math import floor

Order = namedtuple('Order', ['label', 'pmax', 'umax']);
OrderGroup = namedtuple('OrderGroup', ['labels', 'p', 'u'])
Bundle = namedtuple('Bundle', ['label', 'p', 'q'])
PersonalResult = namedtuple('PersonalResult', ['label', 'p', 'q', 'u'])
BundleResult = namedtuple('BundleResult', ['label', 'n', 'ptotal', 'qtotal'])


def print_bulkfoods(bundles, orders):
    bundle_results, personal_results = bulkfoods(bundles, orders)
    print("Bundles")
    for br in bundle_results:
        print("\t{}\tn={}\tptotal={:.2f}\tqtotal={:.2f}".format(br.label, br.n, float(br.ptotal), float(br.qtotal)))
    print()

    print("Personal Results")
    for pr in personal_results:
        print("\t{}\tp={:5.2f}\tq={:.2f}\tu={:.2f}".format(pr.label, float(pr.p), float(pr.q), float(pr.u)))


def bulkfoods(bundles, orders):
    # recursively try all affordable bundles
    bundle_counts, order_groups = _try_all_bundles(bundles, orders)
    if order_groups is None:
        return None, None

    label_to_order = {}
    for o in orders:
        label_to_order[o.label] = o

    personal_results = []
    for g in order_groups:
        labels = sorted(g.labels, key=lambda l: label_to_order[l].pmax)
        p_remaining = g.p
        for i in range(len(labels)):
            labels_remaining = len(labels) - i
            label = labels[i]
            order = label_to_order[label]
            p_current = min(order.pmax, p_remaining / labels_remaining)
            p_remaining -= p_current
            personal_results.append(PersonalResult(label, p_current, p_current / g.u, g.u))
        assert abs(p_remaining) < 1e-2, p_remaining

    bundle_results = []
    for i in range(len(bundle_counts)):
        b = bundles[i]
        c = bundle_counts[i]
        if c > 0:
            bundle_results.append(BundleResult(b.label, c, b.p * c, b.q * c))

    return bundle_results, personal_results


def _try_all_bundles(bundles, orders):
    # No two bundles have the same efficiency, and if we bought 2 bundles of different efficiency
    # then we'd be better off not buying the less efficient one, scaling down price accordingly,
    # and distributing extra quantity to lower unit price. Thus we will only buy one type of bundle
    best_bundle = None
    best_count = None
    best_quantity = 0
    best_groups = None

    pmax = sum([o.pmax for o in orders])
    for i in range(len(bundles)):
        for count in range(1, floor(pmax / bundles[i].p) + 1):
            p_total = count * bundles[i].p
            q_total = count * bundles[i].q
            groups = _bulkfoods(p_total, q_total, orders)
            if groups:
                if (best_groups == None
                    or best_groups[-1].u > groups[-1].u
                    or (best_groups[-1].u == groups[-1].u and q_total > best_quantity)
                ):
                    best_bundle = i
                    best_count = count
                    best_quantity = q_total
                    best_groups = groups

    counts = [(best_count if i == best_bundle else 0) for i in range(len(bundles))]
    return counts, best_groups


# helper function used when a set of bundles has been selected, determining p_total and q_total
# produces the allocation of P and Q to (groups of) people
def _bulkfoods(p_total, q_total, orders):
    if q_total <= 0:
        return None

    # sort orders by max unit price
    orders = sorted(orders, key=lambda o: o.umax)

    # convert from orders to order groups so we can combine orders that are at the same unit price
    merge_groups = lambda g1, g2: g1._replace(labels=g1.labels + g2.labels, p=g1.p + g2.p, u=min(g1.u, g2.u))
    groups = []
    for o in orders:
        g = OrderGroup(labels=[o.label], p=o.pmax, u=o.umax)
        if groups and groups[-1].u == g.u:
            groups[-1] = merge_groups(groups[-1], g)
        else:
            groups.append(g)

    # Perform first sweep, to determine which groups are in on the purchase
    p_purchase = 0
    min_group = len(groups)
    for i in range(len(groups) -1, -1, -1):
        if p_purchase < p_total:
            min_group = i
        group_p = min(groups[i].p, p_total - p_purchase)
        groups[i] = groups[i]._replace(p=group_p)
        p_purchase += group_p
    if p_purchase < p_total:
        return None
    groups = groups[min_group:]

    # Perform second sweep, to determine the unit price paid by each group
    q_remaining = q_total
    p_remaining = p_total
    for i in range(len(groups)):
        u_group = min(p_remaining / q_remaining, groups[i].u)
        groups[i] = groups[i]._replace(u=u_group)
        p_remaining -= groups[i].p
        q_remaining -= groups[i].p / u_group
        if q_remaining < -1e-2:
            return None

    # Done!
    return groups