#!/usr/bin/env python

import sys

from gsp import GSP
from util import argmax_index

class GleaningWitBudget:
    """Budgeted"""
    def __init__(self, id, value, budget):
        self.id = id
        self.value = value
        self.budget = budget
        self.spending = 0
        print "My value is {} and id {}".format(value, id)

    def initial_bid(self, reserve):
        return self.value / 2

    def slot_info(self, t, history, reserve):
        """Compute the following for each slot, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns list of tuples [(slot_id, min_bid, max_bid)], where
        min_bid is the bid needed to tie the other-agent bid for that slot
        in the last round.  If slot_id = 0, max_bid is 2* min_bid.
        Otherwise, it's the next highest min_bid (so bidding between min_bid
        and max_bid would result in ending up in that slot)
        """
        pr = history.round(t-1)
        other_bids = filter(lambda (a_id, b): a_id != self.id, pr.bids)

        clicks = pr.clicks
        def compute(s):
            (min, max) = GSP.bid_range_for_slot(s, clicks, reserve, other_bids)
            if max == None:
                max = 2 * min
            return (s, min, max)
            
        info = map(compute, range(len(clicks)))
#        sys.stdout.write("slot info: %s\n" % info)
        return info


    def expected_utils(self, t, history, reserve):
        """
        Figure out the expected utility of bidding such that we win each
        slot, assuming that everyone else keeps their bids constant from
        the previous round.

        returns a list of utilities per slot.
        """ 
        slot_infos = self.slot_info(t, history, reserve)
        pr = history.round(t-1)
        clicks = pr.clicks

        utilities = [s[1] * (self.value - s[0][1]) for s in zip(slot_infos, clicks)]
        return utilities

    def target_slot(self, t, history, reserve):
        """Figure out the best slot to target, assuming that everyone else
        keeps their bids constant from the previous rounds.

        Returns (slot_id, min_bid, max_bid), where min_bid is the bid needed to tie
        the other-agent bid for that slot in the last round.  If slot_id = 0,
        max_bid is min_bid * 2
        """
        i =  argmax_index(self.expected_utils(t, history, reserve))
        info = self.slot_info(t, history, reserve)
        return info[i]

    # finds the value/dollar for each slot
    def value_per_slot_dollar(self, t, history, reserve):
        pr = history.round(t-1)
        clicks = pr.clicks
        pcp = pr.per_click_payments
        sp = pr.slot_payments
        values = [1.0*clicks[i] * (self.value - pcp[i])/sp[i] for i in
                xrange(len(sp))]
        print 'My values per slot dollar', values
        return values
    
    # determine best slot based on the one with highest value/dollar
    def target_value_slot(self, t, history, reserve):
        i = argmax_index(self.value_per_slot_dollar(t, history, reserve))
        info = self.slot_info(t, history, reserve)
        return info[i]

    def bid(self, t, history, reserve):
        # The Balanced bidding strategy (BB) is the strategy for a player j that, given
        # bids b_{-j},
        # - targets the slot s*_j which maximizes his utility, that is,
        # s*_j = argmax_s {clicks_s (v_j - p_s(j))}.
        # - chooses his bid b' for the next round so as to
        # satisfy the following equation:
        # clicks_{s*_j} (v_j - p_{s*_j}(j)) = clicks_{s*_j-1}(v_j - b')
        # (p_x is the price/click in slot x)
        # If s*_j is the top slot, bid the value v_j
        pr = history.round(t-1)
        print "Round number", t
        if t == 1:
            self.av = [2*x[1] for x in pr.bids]
      
       # for i, x in enumerate(sorted(self.av)):
       #     if abs(self.value - x) <= 1 and i <= 1: 
       #         print "We're in position {}, screw up people!!".format(i)
       #         bid = self.value
       #         return bid
        
        tot_spend = history.agents_spent
        self.spending = tot_spend[self.id]
        bids = pr.bids
        clicks = pr.clicks
        pos = pr.occupants
        pcp = pr.per_click_payments
        sp = pr.slot_payments
        #print "Total spend", tot_spend
        #print "prev bids", bids
        #print "prev clicks", clicks
        #print "occupants", pos
        #print "per click payments", pcp
        #print "slot payments", sp
        values = [clicks[i] * (self.av[p] - pcp[i]) for i,p in enumerate(pos)]
        #print "values", values
        #print "value/dollar", [v/sp[i] for i,v in enumerate(values)]
        
        # if only two guys left, then we don't need to spend anything to get
        # pretty good results
        if len(pr.slot_payments) <= 2:
        #if len(pr.slot_payments) != len(pr.clicks):
            return reserve + 1

        # cruise when lower clicks
        if t > 12 and t < 36:
        #    print "We're cruising, spent", self.spending, "new bid",
        #    sorted(pr.bids)[1][1] + 1
        #    return sorted(pr.bids)[1][1] + 1
            second_highest = sorted(pr.bids)[1]
            if second_highest[1] < self.value and second_highest[1] < 4*reserve:
                return second_highest[1] + 1
            else:
                return reserve + 1
        
        #(slot, min_bid, max_bid) = self.target_slot(t, history, reserve)
        (slot, min_bid, max_bid) = self.target_value_slot(t, history, reserve)
        clicks = pr.clicks
        
        bid = 0
        if min_bid >= self.value: # min price is more than value, then give up
            bid = self.value
        else:
            if slot == 0: # going for the top!
                bid = self.value
            else:
                #bid = min_bid + 1
                bid = self.value - 1.0*clicks[slot]/clicks[slot - 1]*(self.value - min_bid)
        
        num_rounds = 48
        time_left = num_rounds - t
        money_left = self.budget - self.spending
        money_will_spend = bid * clicks[0]
        # if we're going to go over budget, then reduce bid to just enough to
        # stay in game
        if (money_will_spend + self.spending) > self.budget or (time_left *
                reserve * clicks[0]) > money_left:
            return reserve + 1
        
        return bid

    def __repr__(self):
        return "%s(id=%d, value=%d)" % (
            self.__class__.__name__, self.id, self.value)


