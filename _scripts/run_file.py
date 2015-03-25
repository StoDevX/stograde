#!/usr/bin/env python3

import sys, os
from run import run

hw11 = {
  'tiny.txt': '''3
   2 3 7''',
   'firefox2.txt': '''256
   0  123    0    0    0   86   86   86   86   86   86    0    0    0    0    0
   0  123  123   86   86  123   84  206  206  185  125   86   86    0    0    0
   0  123  148  123  123  148   76  192  192  183  145   86  166  106    0    0
   0  123  148  161  148  148   70   70   18  181  153   88  187  177  112    0
  96  142  161  155  142  146  123  123   42  166  154   89  139  209  112    0
  96  150  161  148  137  139  182   70  161  152  133   93  105  195  173  111
  96  153  161  142  168  168  183   76  133  124  103   89   66  199  188   98
  96  150  158   92   66   70   70   63   79   79   76   76   82  209  191   98
  96  130  148  142   82   84   55   65  100  119   67   65  114  197  168   98
  96  101  148  148  104  106  114  122  116   70   63   54  167  180  132   98
  96   96  123  148  146  125  103   84   70   55   80  141  175  152  101   98
   0   90   96  142  148  139  134   85  101  103  123  148  150  122  101    0
   0   90   84   96  129  142  142  142  142  136  129  136  133  106  101    0
   0    0   84   90   90  100  112  112  117  117  117  106   96   76    0    0
   0    0    0   64   64   76   92   92   92   92   90   64   64    0    0    0
   0    0    0    0    0   64   64   64   64   64   64    0    0    0    0    0'''
}

input_files = {
  'hw11': hw11,
}

empty = {'empty': ''}


def run_file(hw, filePath):
  items = input_files.get(hw, empty).items()
  results = []
  for inputName, inputFile in items:
    result = run([filePath], input=inputFile, timeout=4)
    results.append((inputName, result))

  return '\n'.join(['%s: \n\n%s\n\n' % (inputFile, result) for inputFile, result in results])


if __name__ == '__main__':
  hw = sys.argv[1]
  filePath = sys.argv[2]
  print(run_file(hw, filePath))
