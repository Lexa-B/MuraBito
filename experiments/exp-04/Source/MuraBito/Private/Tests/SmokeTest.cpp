#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSmokeTest, "MuraBito.Smoke",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FSmokeTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("one plus one"), 1 + 1, 2);
	return true;
}

#endif
