// The only place tiadump may compile. Used for units of the WORKING COPY that
// SIMATIC SD cannot export (GRAPH, ProDiag, S7-300/400) and that are inconsistent, so that the
// SimaticML export accepts them. The source project and every device stay untouched; the
// caller records the compiled units in the dump (manifest) and turns failures into gaps.
using System.Collections.Generic;
using Siemens.Engineering;
using Siemens.Engineering.Compiler;

namespace TiaDump.Openness
{
    public static class CopyCompiler
    {
        public sealed class Result
        {
            public bool Ok;
            public List<string> Messages = new List<string>();
        }

        public static Result CompileUnit(IEngineeringServiceProvider unit)
        {
            var result = new Result();
            var compilable = unit.GetService<ICompilable>();
            if (compilable == null)
            {
                result.Messages.Add("unit cannot be compiled through Openness");
                return result;
            }
            var r = compilable.Compile();
            result.Ok = r.State != CompilerResultState.Error;
            Collect(r.Messages, result.Messages, 0);
            return result;
        }

        private static void Collect(CompilerResultMessageComposition messages, List<string> into, int depth)
        {
            foreach (CompilerResultMessage m in messages)
            {
                if (m.State == CompilerResultState.Error || m.State == CompilerResultState.Warning)
                    into.Add($"{m.State}: {m.Path} {m.Description}".Trim());
                if (depth < 6) Collect(m.Messages, into, depth + 1);
            }
        }
    }
}
