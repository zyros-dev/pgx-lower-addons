# Development Blog
> This is half written at the moment! Check back later (Early December!)

This contains interesting the path I took while making this as well as interesting problems I encountered. To understand it, you should require some level of understanding of what a compiler is, what a database's internals are, and some C++ knowledge. You should not require an understanding of the nodes in PostgreSQL (e.g. what is an Aggref and how do we parse it?), or what MLIR actually is.

## Background research
This content is optional, and more  a record of prior research. A literature review was conducted, which you can read HERE `TODO: Add a hyperlink to the download button for it... it's in the resources folder of the website...`. This is quite long, and not that relevant to writing the extension. So I won't dive into it.

My Notion pages have some sections on this: https://www.notion.so/zyros/Compiled-PostgreSQL-1bed636b94f0805990a6ca1a931586bb . These are from a much earlier stage of this project, and might not be valid.

The TLDR is that most databases use a volcano/interpreter execution model where it builds a tree of functions from your SQL, then runs it bottom-up. So the leaf node reads a tuple, then it goes up and gets filtered, then projected. Recently, a number of databases (HyPER) found that with modern systems the persistent storage is fast enough to justify compiling the queries using a serious compiler. So, this project's aim is to make an extension for Postgres that uses MLIR to compile queries and execute them.

## Initializing the code
Starting the codebase was quite challenging, as I was quite new to large-scale C++ codebases. At first I started on a MacOS system, but hit so many pains over the course of several weekends that I eventually gave up. Previously, I had a small computer with Linux that I used whenever I needed OS-level operations. However, in this case, it's a long term project so I swapped over my primary computer instead. Plus the windows 10 end of life was coming up so it was a good opportunity for that.

My initial idea for the project was that I'd take Postgres, create an extension, then throw the SQL straight into [lingo-db](https://github.com/lingo-db/lingo-db?tab=readme-ov-file), however, that quickly hit a lot of problems. The idea is like this:
![[Pasted image 20251021081152.png]]

I stumbled upon [this codebase](https://github.com/mkindahl/pg_extension) to initialise a postgres extension and got started with the idea. I had to find the hooks to take over the execution engine:

https://doxygen.postgresql.org/executor_8h_source.html
![[Pasted image 20251022052921.png]]
This worked quite well! I could dip into our extension, then return back out of Postgres; doing nothing inside except log. Next, let's install Lingo-DB... annnd that's where I hit a lot of problems. LingoDB actually [forked LLVM and added their own patches to it](https://github.com/jungmair/llvm-project), and LingoDB uses [arrow files](https://arrow.apache.org/docs/python/index.html) for persistent storage. I don't want that, I want to lean on Postgres! Thus ensued a stage of me ripping out parts of LingoDB, compiling, failing to compile, and so on for a few weekends.

Once I could actually access MLIR, LLVM, and compile while touching parts of LingoDB with my codebase, it was time to move onto creating a testing platform. The boilerplate repository I mentioned earlier came along with tooling for pg_regression. My initial idea here was I'd put TPC-H in there, and work through it one query at a time... Then I realised how complex and painful TPC-H actually is. Instead, I had to hand write from the ground up very very VERY simple queries. This started with `1_one_tuple.sql`, which puts a single integer in the database then fetches it.

Remember how I said I wanted to throw LingoDB in as a module, then throw the raw SQL in? So, that's a bad idea fundamentally. I tried to do it, and it was mostly a waste of time. This was probably about a weekend, and after losing a chunk of my sanity I ended up throwing away my entire project, starting again, and renamed it from `psql-mlir-jit` to `pgx-lower`!

![[Pasted image 20251021082049.png]]

The issue is quite obvious. I'm throwing away all the work Postgres did! Instead, I need to harvest out the _plan tree_. This is opposed to the _query tree_. This is the first fundamental mismatch between us and LingoDB. LingoDB imports a PostgreSQL library that parses strings into plan trees, then they parse the plan tree into their high level dialect.  However, we have access to a succulent plan tree for zero cost which has gone through the query optimiser. Sadly, we're going to have to pay for this later as well.

So, I decide let's add my own "PGX dialect". The idea here is that I would "only" use the relalg layer, and it would match Postgres! This was brutally wrong... But it did work for the first ten or so types of queries I made! That set of Notion pages I mentioned earlier goes over this part!
![[Pasted image 20251021082541.png]]

I quickly hit a wall where this just... stopped functioning. Expressions slammed me. If you do A + B, you need to do type casting! But before type casting you need to turn it into PGX Dialect... So, at this point I scrapped the structure _again!_

I stepped back. I had to go understand MLIR and LingoDB! Let's go read their master branch!![[Pasted image 20251021083041.png]]

I quickly found the master branch was too complicated, so I dropped down to their initial paper. Staring at their diagram of how these languages worked, I was quite confused. 
![[Pasted image 20251021083140.png]]

This is their diagram from their paper. Maybe I didn't understand MLIR strongly enough, but I don't see particularly clear definitions of what their dialects and passes were. I thought pass == dialect at this point, and when you go through a pass you're specifically only in a new dialect. This is wrong. MLIR supports mixed dialects, and you can push it through legality filters. 

I read around for a while and settled on this mental picture of their codebase
![[Pasted image 20251021083326.png]]

libpg_query parses the raw string into their relational algebra "dialect". You can log MLIR dialects, or really MLIR "modules" (since they can be mixed) as a string representing code. In reality, underneath, its really a tree structure. This is what you see when you use the "Query" tool on this website.

Alright, cool, so how do we tie this back over to our project?
![[Pasted image 20251021083524.png]]

This is the final structure I settled on! We grab the plan tree, and then check whether we can support this in our analyzer. This continues onto the parser, which turns us into relational algebra. This enters the same pattern as LingoDB once it's parsed. Now, the crucial difference is that LingoDB was using Apache Arrow for storage, but we're using Postgres. We're going to have to rewrite all their access tools and other things. But this structure was stable enough!

At this point, our codebase is already something like 30,000 lines of code from all the boilerplate! However, we're ready to start really digging into how to parse the plan tree, how to link those runtime functions together, and any other struggles!

## Testing structure/flow

As mentioned earlier, we're using pg_regression to push layers of SQL scripts through our system in increasing complexity. This is great, and mostly worked. It starts with one tuple and one column, then two tuples, then several thousand tuples, more data types, expressions, logical expressions, introducing where, and so on. However, I hit a critical issue: Postgres's process model. Postgres has one master process, and when you connect a client it spawns a new process. This is problematic. If I want to attach a debugger, valgrind, or something else, then I need to connect to the database, `select pg_backend_pid();`, then manually launch GDB with that process ID!

My first instinct here was to introduce a `utest` (unit test) module. This would be isolated from Postgres as something where I can put the relational algebra directly into, then see it go through the passes. This worked great! For a while... until I hit a segfault that was in my parser! Over time this module melted away because I started wanting to introduce Postgres APIs within the passes as well.

Within the codebase there's a `debug-query.sh`, which does that whole process earlier but on its own. This is sort of limited in that you need to type the GDB commands beforehand, so there's also a `interactive-tpch-query.sh` that I implemented. It was a lot easier than I expected considering I first did this _several months in_. There are piles of different testing methods I went through before I settled on this. 

One of the biggest time wasters in this was that MLIR and LLVM spit out errors into `stdout` and `stderr`. Postgres doesn't listen to those streams at all. So for a weekend or two, my system was falling over completely silently and I wasn't sure what to do about it. The old unit testing framework solved this since it would listen to those, and I also tried to redirect all the stdout and stderr over, but it didn't always work. Either way, `debug-query.sh`, and `PGX_ERROR` (log command that includes a back trace) ended up being enough to solve all the situations I encountered.


## Case 1: Decimals
* Write about researching how LingoDB handles Decimals into i128
* LingoDB can rely on arrow things
* We can't, so we need to invent our own parsing
* It would be nice to throw decimals all the way through, but that would require us to rewrite a good chunk of the lowerings

## Case 2: Contexts, Scopes and Parameters
* Wrangling how to define data passing through our AST translator
* Talk about how initially I had a query context, then that evolved into TranslationResult representating situational state, and finally QueryContext carrying situational state and translation result just... representing a translation result. So QueryCtxT can flow downwards, but not upwards, and TranslationResult can only flow upwards
* Include a section detailing my pains about "type correctness", and why I basically ended up abandoning it.

## Case 3: 
* I don't know... but it would be good to get three!

## Lessons
* PostgreSQL is a mess... and it is difficult to figure out what the optimizer does
* If I restarted this entire project from scratch now, I would target WebAssembly. WebAssembly is created to trigger JIT very quickly. However, admittedly, when I started I would not have know enough about compilers to do this properly (splitting it into dialects and such). It would have meant that I could skip C++ though.
* C++ pains. C++, in theory, is a great language. But only if every library you're using has the same standard, and the same memory model. In this particular case, I had PostgreSQL, MLIR, LLVM, and my own C++ style colliding. PostgreSQL uses this arena-style allocator, MLIR has its own allocator but doesn't tell you whether something is actually a pointer, and my own code is trying to follow modern C++20; using `unique_ptr` and so on. However, with LLVM as the target you are more or less forced into C++. 