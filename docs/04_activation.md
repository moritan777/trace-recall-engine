# Activation

Activation is the process by which current input causes stored traces to become active.

## Input

The input begins as extracted words.

Example:

```text
Input: 好きなケーキって何だったっけ？
Input Words: 好き / ケーキ
```

## Activation Flow

```text
Input Words
↓
Word Nodes
↓
Threads
↓
Related Words
↓
ThreadGroups
```

## Goal

The goal of activation is not to decide what should be said.

The goal is to reveal what traces react to the current input.

Selection happens later.
