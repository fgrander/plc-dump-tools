// Library type kinds from the Openness classes seen in the library spike.
using TiaDump.Dump;
using Xunit;

namespace TiaDump.Tests
{
    public class LibraryKindTests
    {
        [Theory]
        [InlineData("CodeBlockLibraryType", "plc_block")]
        [InlineData("PlcTypeLibraryType", "plc_type")]
        [InlineData("FaceplateLibraryType", "faceplate")]
        [InlineData("StyleLibraryType", "hmi_type")]
        [InlineData("HmiUdtLibraryType", "hmi_type")]
        [InlineData("ScreenLibraryType", "hmi_type")]
        [InlineData("SomethingNewLibraryType", "other")]
        public void KindFromOpennessClass(string clr, string kind) => Assert.Equal(kind, LibraryDumper.KindOf(clr));
    }
}
