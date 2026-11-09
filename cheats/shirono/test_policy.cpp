#include <cstdio>
#include "clone_policy.h"
static_assert(shirono::kNativeCloneObjectId == 19, "AGTK project ID");
static_assert(shirono::kObjectCreateRva == 0x1284A0, "Ghidra RVA");
static_assert(shirono::ExtraSpawnsFor(19, 2) == 2, "2 extra clones");
static_assert(shirono::ExtraSpawnsFor(1, 2) == 0, "No player replication");
static_assert(shirono::ExtraSpawnsFor(19, -1) == 0, "Invalid negative setting");
static_assert(shirono::ExtraSpawnsFor(19, 7) == 0, "Reject oversized counts");
int main() {
    for (int n=0;n<=6;n++) if(shirono::ExtraSpawnsFor(19,n)!=n)return 1;
    puts("SHIRONO_POLICY_PASS native_id=19 extras=0..6");
    return 0;
}
