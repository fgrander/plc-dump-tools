// Canonical JSON is deterministic.
using System.Collections.Generic;
using TiaDump.Dump;
using Xunit;

namespace TiaDump.Tests
{
    public class JsonTests
    {
        [Fact]
        public void SameGraphGivesByteIdenticalSortedOutput()
        {
            var a = new Dictionary<string, object?> { ["b"] = 1, ["a"] = new List<object?> { "x", null, true, 1.5 } };
            var b = new Dictionary<string, object?> { ["a"] = new List<object?> { "x", null, true, 1.5 }, ["b"] = 1 };
            Assert.Equal(Json.Serialize(a), Json.Serialize(b));
            Assert.Equal("{\n  \"a\": [\n    \"x\",\n    null,\n    true,\n    1.5\n  ],\n  \"b\": 1\n}\n", Json.Serialize(a));
        }

        [Fact]
        public void StringsAreEscaped()
        {
            Assert.Equal("\"a\\\"b\\\\c\\n\\u0001\"\n", Json.Serialize("a\"b\\c\n\u0001"));
        }
    }
}
