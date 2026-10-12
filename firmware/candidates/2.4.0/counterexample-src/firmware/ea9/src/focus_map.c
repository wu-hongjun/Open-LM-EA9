#include "focus_map.h"

int32_t focus_counts_to_reference(int32_t c)
{
    if (c < 0) c = 0;
    if (c > FOCUS_TRAVEL_COUNTS) c = FOCUS_TRAVEL_COUNTS;
    return c + FOCUS_REFERENCE_OFFSET;
}
int32_t focus_reference_to_counts(int32_t r)
{
    if (r <= FOCUS_REFERENCE_OFFSET) return 0;
    if (r >= FOCUS_REFERENCE_OFFSET + FOCUS_TRAVEL_COUNTS) return FOCUS_TRAVEL_COUNTS;
    return r - FOCUS_REFERENCE_OFFSET;
}

int32_t focus_em06_to_counts(uint16_t pos)
{
	int32_t c;

	if (pos <= FOCUS_EM06_LO) {
		return 0;
	}
	c = ((int32_t)pos - FOCUS_FACTORY_ORIGIN) * FOCUS_COUNTS_PER_UNIT;
	return focus_reference_to_counts(c);
}

uint16_t focus_counts_to_em06(int32_t counts)
{
	if (counts < 0) {
		counts = 0;
	} else if (counts > FOCUS_TRAVEL_COUNTS) {
		counts = FOCUS_TRAVEL_COUNTS;
	}
	return (uint16_t)(FOCUS_FACTORY_ORIGIN + focus_counts_to_reference(counts) / FOCUS_COUNTS_PER_UNIT);
}
