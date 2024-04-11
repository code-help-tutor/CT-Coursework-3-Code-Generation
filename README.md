![BuildAndTest](../../workflows/BuildAndTest/badge.svg?branch=main) ![Points badge](../../blob/badges/.github/badges/points.svg)

# CT 2022/23 | Coursework 3 - Code Generation

**Deadline:** Fri, 31.03.2023 (Week 11), 22:00  
## Provided

This coursework already provides:

- I) Lowering from the choco AST (`choco.ast`) to a flat version of the choco AST (`choco.ir`).
- II) A skeleton for lowering the `choco.ir` to an SSA RISCV-V dialect (`riscv_ssa`).
- III) Lowering from `riscv_ssa` to a dialect for RISC-V assembly (`riscv`).
- IV) A printer for the `riscv` dialect which emits assembly files.


## Tasks
1. Core: Code generation
2. Expert: Optimization


## Quick Install (for DICE-like environments)

### Download This Coursework

First, you will need to **clone** the repository. If you used GitHub before, you will already have either an HTTPS access token, or an SSH key. If you do not have either, you will need to create this. You can use either, just follow the guides below:
  - To create an SSH key, use [this](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
  - To create an HTTPS token, use [this](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
    At some point, you will be asked to specify what you want to do with the token: feel free to tick all the boxes.

  At this point, you can clone the repository:
  - if you used HTTPS above, use the command
    ```
    git clone https://github.com/compiling-techniques/REPOSITORY_NAME.git
    ```
  - if you used SSH, use the command
    ```
    git clone git@github.com:compiling-techniques/REPOSITORY_NAME.git
    ```
Now enter the repository directory: `cd REPOSITORY_NAME`. If this is your first time using Git, you will need to set up a bit of configuration:
  ```
  git config --global user.name "your_github_username"
  git config --global user.email "your_github_email"
  ```
  This will set your username and email globally (for all repositories, unless they overwrite this), so all future GitHub repositories will already have this set up. If you do not wish to do that, just omit the `--global`.
  You can verify the setup using `git config -l`, which will just tell you what settings you set.

### Installation

You can create an isolated python environment using [venv](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment).
To set up `venv` for the assignment, follow the steps below (a summary is given below the bulleted list):

1. Set up a virtual environment for the assignment with `python3 -m venv env`.
   This creates a subdirectory called `env` in the current folder that creates an isolated version of Python.
2. Activate the virtual environment by [`source`ing](https://linuxcommand.org/lc3_man_pages/sourceh.html) the activation file: `source env/bin/activate`
3. Confirm that you are in the virtual environment by running `which python`. The output should be `/path/to/coursework/env/bin/python`.
4. Run `pip install -U -r requirements.txt` to install dependencies within the virtual environment.
5. Run `pip install -e .` to install the ChocoPy compiler as a package.
6. If you are using PyCharm, please configure PyCharm to work with the environment by following the instructions on
   this page of the PyCharm manual: [Configure a virtual environment](https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html).

In summary, the process looks as follows:

```bash
/path/to/coursework$ /afs/inf.ed.ac.uk/group/teaching/ct/python/3.10/bin/python3.10 -m venv env # set up virtual environment called `env`

/path/to/coursework$ source env/bin/activate # run activation file

(env) /path/to/coursework$ # (env) shows up

(env) /path/to/coursework$ which python # confirm python path
/path/to/coursework/env/bin/python

(env) /path/to/coursework$ pip install -U -r requirements.txt # install dependencies

(env) /path/to/coursework$ pip install -e . # install ChocoPy as a package

(env) /path/to/coursework$ # get to hacking, and best of luck! :)
```

#### PyCharm

It would be convenient for you, if you used a modern IDE for Python.
A popular choice, `PyCharm`, comes pre-installed in your DICE desktop environment.

If you decide to use `PyCharm`, in order to install the packages, you should open the embedded terminal (`Alt+F12` by default)
and follow the previous instructions using `pip install -U -r requirements.txt`.

#### Using GitHub code spaces

Instead of cloning the repository to your local machine, you can also use GitHub codespaces to do your coursework. This is a beta-test, so it is an optional offer that is delivered on a best-effort basis. TO use GitHub codespaces click on the green "Code" button at the top of this repository, select "code spaces" and create your personal codespace. Then enter the console and run:

```bash
$ export PATH=/home/codespace/.local/lib/python3.10/site-packages/bin/:$PATH
$ pip install -U -r requirements.txt # install dependencies
$ pip install -e . # install ChocoPy as a package
$ # get to hacking, and best of luck! :)
```

### Test your solutions

You can use `lit` to automatically test your code, which is include in the `requirements.txt`.

To run it locally, do:

```bash
lit -v tests/end-to-end
```

This will examine recursively all the files with valid formats inside the above directory.
The `-v` flag adds a verbose output with more information in case some tests fail.
You can also leverage the `--timeout <seconds>` flag, in order to bound the time allowed for your test cases to run.
This way you can detect if your parser loops infinitely in some test cases.

For more details on the configuration of `lit`, see `tests/lit.cfg`.
For more info on `lit` check the [online documentation](https://filecheck.readthedocs.io/en/latest/01-what-is-filecheck.html).

## Task 1 - Code Generation

The goal of task 1 is to write a code generator for the [ChocoPy Language](https://chocopy.org), targeting the [RISC-V architecture](https://riscv.org/).
The output RISC-V program will be run on a RISC-V interpreter.

In particular, you need to implement the lowering from the `choco.ir` dialect to the `riscv_ssa` dialect.
The template already provides a partial implementation of the lowering.
You will have to implement the rest.

### 1. Getting Started
**First read this README completely and carefully!**
It explains the lowering phases of the code generation, as well as how to run the assembly code.
We have also added some [hints](#6-Hints) that are useful for this coursework.

To understand how lowering from `choco.ast` to `choco.ir` works (step I), have a look at `choco/choco_ast_to_choco_flat.py`.
After you have a quick look, it would be particularly useful for understanding the next steps, if you get a good understanding of the following files:

* `choco/choco_flat_introduce_library_calls.py`
* `choco/for_to_while.py`

The `choco.ir` dialect is described in `choco/dialects/choco_flat.py`.

### 2. RISC-V SSA Dialect

To understand how you should lower `choco.ir` to `riscv_ssa` (step II), you need look at what RISC-V instructions are available in the class `RISCVSSA` of `riscv/ssa_dialect.py`.

Each instruction subclasses a RISC-V Operation, e.g., `Riscv1Rd1Rs1ImmOperation`, which tells you how to use this particular instruction.
For example, the aforementioned operation uses one destination register (`Rd`), one source register (`Rs`) and one immediate (`Imm`).
A RISC-V instruction that corresponds to this encoding is `AddIOp`, which adds an immediate to the source register, and places the result on the destination register.

### 3. Runtime Library

We give you the implementation of the runtime library, which is automatically added to your riscv programs. Some of the library function calls are already generated by the frontend, but you will need to generate some calls for these functions:
* `_malloc`: Allocate in the heap the number of bytes given as argument, and return a pointer to it.
* `_error_len_none`: Print an error and exit the program. This should be used when `len` is called on a `None` value.
* `_list_index_oob`: Print an error and exit the program. This should be used when an array is accessed out of bounds.
* `_list_index_none`: Print an error and exit the program. This should be used when `None` is indexed.

### 4. Rewriter API

In order to transform the IRs, you will need to use the xDSL rewriter engine.
Here is for instance the given skeleton for the `UnaryExpr` rewrite pattern:
```
class UnaryExprPattern(RewritePattern):

    @op_type_rewrite_pattern
    def match_and_rewrite(self, unary_op: UnaryExpr,
                          rewriter: PatternRewriter):
        raise NotImplementedError()
```

The `match_and_rewrite` method will be called for each `UnaryExpr` in the IR.
The `rewriter` argument has multiple methods that you will need to use throughout the coursework:
* `insert_op_before_matched_op`: Inserts new operations given as inputs before the matched operation (`unary_op` here).
* `erase_matched_op`: Erase the matched operation. If the matched operation had results that are still used, this will trigger an error.
* `erase_op`: Erase the given operation. The given operation should either be the matched
  operation, or an operation contained in the matched operation's regions and blocks. If the
  given operation had results that are still used, this will trigger an error.
* `replace_matched_op`: Replace the matched operation with new operations given as input. The
  SSA results of the matched operation will be replaced by the SSA results of the last given
  operation. Optionally, you can provide a list of SSA values to replace the results of the
  matched operation.
* `inline_block_before_matched_op`: Move the operations in a block right before the matched operation.

Note that `insert_op_before_matched_op` and `inline_block_before_matched_op` should not be used after `replace_matched_op` or `erase_matched_op`.

### 5. Coding

To get started coding look at the file `choco/choco_flat_to_riscv_ssa.py` which contains an incomplete implementation of the lowering to `riscv_ssa`.

The file contains:

- An example rewrite pattern for call expressions.
- A utility function to call the rewriters that lower `choco.ir` to `riscv_ssa`.

**You will need to complete the implementations of the other rewrite patterns**.


#### We suggest the following order when implementing the rewrite patterns:

1. Literals (except strings)
2. Unary expressions (arithmetic and logical)
3. Arithmetic binary expressions
4. Assign statements (alloca, load, store)
5. If statements
6. Logical and conditional expressions
7. While statements
8. List expressions
9. Index operation
10. String literals and string operations

The `tests/end-to-end` folder contains a directory for each section,
making it easier to check your progress.

Now, you can actually execute a ChocoPy program!
First, you can get the RISC-V assembly, by doing:

```bash
cd /path/to/coursework
choco-opt -p all -t riscv tests/end-to-end/print-integer-literal.choc
```

Second, you can run the RISC-V assembly, using the `riscv-interpreter` tool:

```bash
riscv-interpreter tests/riscv/interpreter/hello_world.s
```

Finally, you can combine the above tools in order to execute directly a ChocoPy program:

```bash
cd /path/to/coursework
choco-opt -p all -t riscv tests/end-to-end/print-integer-literal.choc >temp.s && riscv-interpreter temp.s
```

Also, take a look at how `lit` will run tests with filecheck, examining the first line of, e.g., `tests/end-to-end/print-integer-literal.choc`.

### 6. Simplifications

In your implementation, values will all be unboxed, meaning that they do not carry type information.
However, with unboxed, it is not possible to use any value of type `object`, since we
cannot recover its original type statically. To simplify your implementation, we will thus not test
any code that has `object` values, or heterogeneous lists. In particular, this include expressions
such as `if True then 2 else "foo"`, or `[0, True]`.

Similarly, we only support `print` with a `bool`, `int`, or `str` input.

### 7. Hints

#### Alloca, Load, Store

Initially, you can check the correct implementation of `Alloca`, `Store` and `Load`, using the test cases inside `end-to-end/var-defs`.
`Alloca` and `Store` are necessary for variable definitions, `Store` is also necessary for assignments, and `Load` is necessary whenever you are accessing a variable.

#### and, or, and if/else expressions

The `and`, `or`, and `if/else` expressions use short-circuit evaluation. This
means that in the case of an `and` for instance, `False and foo()` will not lead
to the execution of `foo`, since `and` will return `False` for any value
returned by `foo`. This is important in the case where `foo` has a side-effect.

`and`, `or`, and `if/else` expressions use regions to separate both "branches".
Since both branches can have SSA variables, the "result" of a branch is given by
the `yield` operation. Here is for instance the code for `0 > 1 or 1 >= 2`:

```
builtin.module() {
  choco.ir.func_def() ["func_name" = "_main", "return_type" = !choco.ir.named_type<"<None>">] {
    %0 : !choco.ir.named_type<"bool"> = choco.ir.effectful_binary_expr() ["op" = "or"] {
      %1 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 0 : !i32]
      %2 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 1 : !i32]
      %3 : !choco.ir.named_type<"bool"> = choco.ir.binary_expr(%1 : !choco.ir.named_type<"int">, %2 : !choco.ir.named_type<"int">) ["op" = ">"]
      choco.ir.yield(%3 : !choco.ir.named_type<"bool">)
    } {
      %4 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 1 : !i32]
      %5 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 2 : !i32]
      %6 : !choco.ir.named_type<"bool"> = choco.ir.binary_expr(%4 : !choco.ir.named_type<"int">, %5 : !choco.ir.named_type<"int">) ["op" = ">="]
      choco.ir.yield(%6 : !choco.ir.named_type<"bool">)
    }
  }
}
```

#### If Statement

Things will start to become more difficult with control flow.
Essentially, control flow constructs will be needed for if-else statements, while statements, but also for the logical binary expressions (`and`/`or`) and the conditional expression.

Assume the following program:

```python
if True:
  42
else:
  17
```

You can see what is the `choco.ir` form of this program by running:

```
$ choco-opt -p check-assign-target,name-analysis,type-checking,choco-ast-to-choco-flat,choco-flat-introduce-library-calls,for-to-while /path/to/program

builtin.module() {
  choco.ir.func_def() ["func_name" = "_main", "return_type" = !choco.ir.named_type<"<None>">] {
    %0 : !choco.ir.named_type<"bool"> = choco.ir.literal() ["value" = !choco.ir.bool<True>]
    choco.ir.if(%0 : !choco.ir.named_type<"bool">) {
      %1 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 42 : !i32]
    } {
      %2 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 17 : !i32]
    }
  }
}
```

Notice the SSA values created for the condition (`%0`), the value in the if-then block (`%1`), and the value in the if-else block (`%2`).

We sketch how you should approach control flow, when lowering from `choco.ir` to `riscv_ssa`:

1. Assuming that you evaluate conditions by comparing them with zero, you need an SSA value for the constant `0`.
2. You need a RISC-V branch instruction to compare your condition with zero.
3. Since we have control flow, you need labels to represent locations in code, i.e., where is the code for the if-then block, for the if-else block, and for the code after the if statement.
4. If your condition evaluates to false, then you need to jump to the if-else label.
5. Otherwise, you continue with the if-then block, but you also need an extra instruction to jump to the code after the if statement.

The correct `riscv_ssa` output would be:

```
$ choco-opt -p check-assign-target,name-analysis,type-checking,choco-ast-to-choco-flat,choco-flat-introduce-library-calls,for-to-while,choco-flat-to-riscv-ssa /path/to/program

builtin.module() {
  riscv_ssa.func() ["func_name" = "_main"] {
    %0 : !riscv_ssa.reg = riscv_ssa.li() ["immediate" = 1 : !i32]
    %1 : !riscv_ssa.reg = riscv_ssa.li() ["immediate" = 0 : !i32]
    riscv_ssa.beq(%0 : !riscv_ssa.reg, %1 : !riscv_ssa.reg) ["offset" = !riscv.label<if_else_1>]
    riscv_ssa.label() ["label" = !riscv.label<if_then_1>]
    %2 : !riscv_ssa.reg = riscv_ssa.li() ["immediate" = 42 : !i32]
    riscv_ssa.j() ["offset" = !riscv.label<if_after_1>]
    riscv_ssa.label() ["label" = !riscv.label<if_else_1>]
    %3 : !riscv_ssa.reg = riscv_ssa.li() ["immediate" = 17 : !i32]
    riscv_ssa.label() ["label" = !riscv.label<if_after_1>]
  }
}
```

There are many things to notice here.

* `%0` is the SSA value of `True` in the condition.
* `%1` is the SSA value of zero.
* `riscv_ssa.beq` compares the condition with zero. If the condition evaluates to zero (i.e., false), we jump to the `if_else_1` label.
* Otherwise, we continue to the if-then block (`if_then_1` label).
* `%2` is the only thing inside the if-then block.
* `riscv_ssa.j` jumps over the if-else block to the code after if (`if_after_1` label).
* `%3` is the only thing inside the if-else block.

In order to generate branch instructions in the `riscv_ssa` dialect, you can choose one of the `BEQOp`, `BNEOp`, etc.
See the `ricsv/ssa_dialect` for more details.

These instructions are of `Riscv2Rs1OffOperation` type, which means that they take two SSA values and one offset as an argument.
The offset should be a string representing the label name to which you are branching.

A final thing to keep in mind is that each label name should be unique.
If you use for the `if_then_label` variable the string `"if_then"`, and your program contains multiple if statements,
you will end up with identical label names (which is wrong).

Use the counters provided in the rewrite patterns to get unique names for your labels.

## Task 2 - Code Optimization

The goal of this task is to optimize the code in terms of code size,
that is to reduce the generated lines of RISC-V assembly.

We give examples of different forms below.

### Getting Started

For this task, you can modify or add any pass you want, at any level (dialect) of the compilation pipeline.
We only ask you to not modify nor remove the library calls, nor change the command line API.
Be careful that your optimizations are correct, because otherwise you might lose points in task 1 as well!

The files in `tests/end-to-end/code-size-optimization` contain examples that have some optimization opportunities.
We recommend you to implement these optimizations (in order of difficulty):
* Constant folding (you can continue the implementation of `choco/constant_folding.py`)
* Some arithmetic rewrite rules (such as `x * 0 = 0`, or `(x + 3) + 5 = x + 8`)
* Removal of unnecessary `load`/`store` for temporary chocopy variables.
* Improving the register allocator to not always spill registers on the stack.
  This can be done in a pass after the translation of riscv-ssa to riscv, or by modifying
  the register allocator (hard, but would yield better code reduction).

We include two minimal examples of rewriters, which operate on the `choco.ir` level.
So, you need to have a good understanding of the following files:

* `choco/constant_folding.py`
* `choco/dead_code_elimination.py`

### Adding a new pass to `choco-opt`

We take as similar approach as in `choco/constant_folding.py`.

First, you need to create a similar file, e.g., `choco/your_new_pass.py`.

Then, this file can contain your rewriter pattern and a function that will invoke the `PatternRewriteWalker` with your rewriter.
For example, this function could be called `choco_flat_your_new_pass`, assuming that your new pass operates on `choco.ir` (choco flat).

Finally, you need to import this invocation function from `choco-opt`, by including:

```python
from choco.your_new_pass import choco_flat_your_new_pass
```

and, also, you need to add the function into the `passes_native` list:

```python
    passes_native = [
        # Semantic Analysis
        check_assign_target,
        # ...

        # IR Optimization
        # ...
        choco_flat_your_new_pass,

        # Code Generation
        # ...
    ]

```



Adding a new separate pass could help with development and debugging, as you can include only some of your passes in `choco-opt` invocation and see if one of them is causing an error.

In particular, instead of passing `-p all` to `choco-opt`, you can be explicit about the passes:


```bash
cd /path/to/coursework
choco-opt -p check-assign-target,name-analysis,type-checking,warn-dead-code,choco-ast-to-choco-flat,choco-flat-introduce-library-calls,choco-flat-constant-folding,choco-flat-dead-code-elimination,for-to-while,choco-flat-to-riscv-ssa,riscv-ssa-to-riscv,riscv-function-lowering -t riscv tests/end-to-end/print-integer-literal.choc
```

Notice the `choco-flat-constant-folding` and `choco-flat-dead-code-elimination` passes.
You could remove or add more passes likewise.
Run:

```bash
choco-opt -h
```

for more info.

If you want to always use the `-p all` flag for brevity, you can also comment out the pass you want to remove from the `passes_native` list in `choco-opt`.

### Examples

#### Dead code elimination in the `choco.ir`:

The code:
```
builtin.module() {
  choco.ir.func_def() ["func_name" = "_main", "return_type" = !choco.ir.named_type<"<None>">] {
    %0 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 42 : !i32]
    %1 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 8 : !i32]
    choco.ir.call_expr(%0 : !choco.ir.named_type<"int">) ["func_name" = "print"]
  }
}
```
can be converted to:
```
builtin.module() {
  choco.ir.func_def() ["func_name" = "_main", "return_type" = !choco.ir.named_type<"<None>">] {
    %0 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 42 : !i32]
    choco.ir.call_expr(%0 : !choco.ir.named_type<"int">) ["func_name" = "print"]
  }
}
```
where the SSA value `%1` was removed since it was not used later.

#### Constant propagation and dead code elimination in the `choco.ir`:

The code:
```
builtin.module() {
  choco.ir.func_def() ["func_name" = "_main", "return_type" = !choco.ir.named_type<"<None>">] {
    %0 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 42 : !i32]
    %1 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 8 : !i32]
    %2 : !choco.ir.named_type<"int"> = choco.ir.binary_expr(%0 : !choco.ir.named_type<"int">, %1 : !choco.ir.named_type<"int">) ["op" = "+"]
    choco.ir.call_expr(%2 : !choco.ir.named_type<"int">) ["func_name" = "print"]
  }
}
```

can be converted to:

```
builtin.module() {
  choco.ir.func_def() ["func_name" = "_main", "return_type" = !choco.ir.named_type<"<None>">] {
    %0 : !choco.ir.named_type<"int"> = choco.ir.literal() ["value" = 50 : !i32]
    choco.ir.call_expr(%0 : !choco.ir.named_type<"int">) ["func_name" = "print"]
  }
}
```

where the binary expression was replaced by the sum of the constants,
and the SSA values `%1` and `%2` were eliminated as dead.
The dead code elimination was enabled by the constant propagation.

## Implementation guidelines

###  Commit and push your changes to GitHub

You are encouraged to commit your changes regularly.
This allows you to track
the history of your changes so that you can revert to an earlier version of your code if you need to.
It also protects you from losing any of your work in the case of a computer failure.

Furthermore, every time you commit and push your changes in the `main` branch, your points are updated,
giving you continuous feedback on your implementation.

### Check your points

This badge shows how many successful test cases you've had so far.

 ![Points badge](../../blob/badges/.github/badges/points.svg)

These points are **provisional** and are not related to the final grade.
The number of successful test cases is only an indicator of how strong your implementation is,
with respect to how many language features it covers.
Your parser will be tested also on other test cases,
so it is important that you write your own tests to ensure that your code is thoroughly tested.

Once you have pushed all of your changes to GitHub and you are happy with your code and your points, you're finished! We will grade your last submission.
Submissions after the deadline, will result in penalties without an approved extension. See "Assessment" on Learn for details.

## Misc

Follow our academic guidelines and take advantage of Piazza to discuss any open questions.

For the following courseworks, the full lexer and parser will be provided.

### Guidelines
Please remember the good scholarly practice requirements of the University regarding work for credit.

The number of passing test cases is intended to give you an idea of the quality of the code.
However, the actual grading of your coursework takes place after the deadline and takes into account public and hidden automatic tests, as well as potential manual reviews.

Submitted code will be checked for similarity with other submissions using the MOSS system. MOSS has been effective in the past at finding similarities and it is not fooled by name changes or reordering of code blocks. Courseworks are INDIVIDUAL, and we expect everyone to turn in their sole, independent work.

Extensions: Please refer to the "Assessment" page on Learn for information on extensions.

### Questions
If you have questions, you should consult the lecture slides and recordings. If you have questions about the coursework, please start by **checking existing discussions on Piazza**. If you can't find the answer to your question, start a new discussion. It is quite possible that other students will have encountered and solved the same problem and will be able to help you. The TA will also monitor Piazza and clarify things as necessary, after allowing time for student discussion to take place.
# CT Coursework 3 Code Generation

# 程序代做代写 CS编程辅导

# WeChat: cstutorcs

# Email: tutorcs@163.com

# CS Tutor

# Code Help

# Programming Help

# Computer Science Tutor

# QQ: 749389476
