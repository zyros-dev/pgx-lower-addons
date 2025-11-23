# I rewrote PostgreSQL's execution engine with an LLVM compiler!

When PostgreSQL was created (1996), people primarily used hard drives with much slower read/write speeds. If you flick through databasing textbooks, we calculate the time complexity based on the read/writes of the disk, and the time in the CPU or RAM is considered completely free. However, with the advent of NVME drives, other SSDs, larger CPU caches and higher RAM, this isn't an entirely valid method of measuring time complexity.

pgx-lower is a PostgreSQL extension that replaces its execution engine with a compiler. It redirects the requests like this below image; parsing it in MLIR, then creating a just-in-time compiled LLVM chunk of code which loops back to the PostgreSQL runtime. This way we can leverage LLVM infrastructure fully.

![PostgreSQL extension diagram](Pasted%20image%2020251005061024.png)

Typically databases use a volcano execution model, which parses your SQL into a plan tree:

![Volcano execution model](Pasted%20image%2020251005060834.png)

(this image is from [Just-in-time Compilation in Vectorized Query Execution](https://homepages.cwi.nl/~boncz/msc/2011-JuliuszSompolski.pdf))

Each node represents a function, and then an iterator is created where you can call `node.next()` for the next tuple value.

Read more at:
* [Presentation Slides B](https://pgx.zyros.dev/api/download/Thesis_B_Anonymous.pdf)
* [Presentation Slides C](https://pgx.zyros.dev/api/download/Thesis_C_Anonymous.pdf)
* [GitHub Repository](https://github.com/zyros-dev/pgx-lower) - Full codebase
* Thesis text will be uploaded mid-December or later