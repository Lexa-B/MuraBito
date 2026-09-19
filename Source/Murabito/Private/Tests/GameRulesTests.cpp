#include "Misc/AutomationTest.h"

#include "GameFramework/DefaultPawn.h"
#include "GameMapsSettings.h"
#include "GameRules.h"
#include "UObject/SoftObjectPath.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	constexpr EAutomationTestFlags GameRulesTestFlags =
		EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGameRulesIsProjectDefaultTest, "Murabito.GameRules.IsProjectDefault", GameRulesTestFlags)
bool FGameRulesIsProjectDefaultTest::RunTest(const FString& Parameters)
{
	const FString Configured = UGameMapsSettings::GetGlobalDefaultGameMode();
	const UClass* Resolved = FSoftClassPath(Configured).TryLoadClass<AGameModeBase>();
	TestTrue(FString::Printf(TEXT("default game mode '%s' is AGameRules"), *Configured), Resolved == AGameRules::StaticClass());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGameRulesKeepsEngineDefaultPawnTest, "Murabito.GameRules.KeepsEngineDefaultPawn", GameRulesTestFlags)
bool FGameRulesKeepsEngineDefaultPawnTest::RunTest(const FString& Parameters)
{
	TestTrue(TEXT("default pawn is the engine's flying camera"),
		GetDefault<AGameRules>()->DefaultPawnClass == ADefaultPawn::StaticClass());
	return true;
}

#endif
