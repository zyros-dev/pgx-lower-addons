# Development Blog
This contains interesting problems I encountered while making this. To understand it, you should require a reasonable understanding of what a compiler is, what a database's internals are, and some C++ knowledge. You should not require an understanding of the nodes in PostgreSQL (e.g. what is an Aggref and how do we parse it?), or what MLIR actually is.

## Background research
This content is optional, and more  a record of prior research. A literature review was conducted, which you can read HERE `TODO: Add a hyperlink to the download button for it... it's in the resources folder of the website...`. This is quite long, and not that relevant to writing the extension. So I won't dive into it.

My Notion pages have some sections on this: https://www.notion.so/zyros/Compiled-PostgreSQL-1bed636b94f0805990a6ca1a931586bb . These are from a much earlier stage of this project, and might not be valid.

## Initializing the code
* Briefly go over the project structures I considered, and the tests I went through. This was quite a lot
* Include a diagram of all the components, and what they mean


## Testing structure/flow
* Include the strategy of mostly relying on pg_regression, but also supporting relalg input into the translator, relalg input into the lowerings, how to connect a debugger to postgresql easily, and in the future profiling and benchmarking...


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