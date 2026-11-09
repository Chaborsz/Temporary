#pragma once
namespace shirono {
inline constexpr int kPlayerObjectId = 1;
inline constexpr int kNativeCloneObjectId = 19;
inline constexpr unsigned kObjectCreateRva = 0x001284A0u;
inline constexpr unsigned char kOriginalPrologue[5] = {0x55,0x8b,0xec,0x6a,0xff};
inline constexpr const char* kExpectedExeSha256 =
    "d91263d4245e029dc0942c1f66bfde712dbc7aeb940737fc3515e48f4f0eb154";
inline constexpr int ExtraSpawnsFor(int targetObjectId, int configuredExtra) {
    return targetObjectId == kNativeCloneObjectId &&
           configuredExtra > 0 && configuredExtra <= 6 ? configuredExtra : 0;
}
}
