#include "Misc/AutomationTest.h"
#include "TerrainHeight.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	constexpr EAutomationTestFlags TerrainTestFlags =
		EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter;

	TArray<FVector2D> SamplePoints()
	{
		TArray<FVector2D> Points;
		for (int32 i = -5; i <= 5; ++i)
		{
			for (int32 j = -5; j <= 5; ++j)
			{
				Points.Add(FVector2D(i * 1234.5, j * 987.6));
			}
		}
		return Points;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainHeightDeterministicTest, "MuraBito.TerrainHeight.Deterministic", TerrainTestFlags)
bool FTerrainHeightDeterministicTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight A(42);
	const FTerrainHeight B(42);
	for (const FVector2D& P : SamplePoints())
	{
		TestEqual(TEXT("same seed, same height"), A.Height(P.X, P.Y), B.Height(P.X, P.Y));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainHeightSeedsDifferTest, "MuraBito.TerrainHeight.SeedsDiffer", TerrainTestFlags)
bool FTerrainHeightSeedsDifferTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight A(1);
	const FTerrainHeight B(2);
	int32 Different = 0;
	for (const FVector2D& P : SamplePoints())
	{
		if (FMath::Abs(A.Height(P.X, P.Y) - B.Height(P.X, P.Y)) > 1.f)
		{
			++Different;
		}
	}
	TestTrue(TEXT("most sample points differ between seeds"), Different > SamplePoints().Num() / 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainHeightRangeTest, "MuraBito.TerrainHeight.Range", TerrainTestFlags)
bool FTerrainHeightRangeTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight H(7, 600.f);
	float Min = TNumericLimits<float>::Max();
	float Max = TNumericLimits<float>::Lowest();
	for (int32 i = -60; i <= 60; ++i)
	{
		for (int32 j = -60; j <= 60; ++j)
		{
			const float Z = H.Height(i * 113.0, j * 113.0);
			Min = FMath::Min(Min, Z);
			Max = FMath::Max(Max, Z);
		}
	}
	// These two can't actually fail: Height() clamps its result to [-Amplitude, Amplitude]
	// (see FTerrainHeight::Height in TerrainHeight.cpp). They document that clamp contract.
	// "has relief" below is the check that would catch a regression here.
	TestTrue(TEXT("never above amplitude"), Max <= 600.f);
	TestTrue(TEXT("never below -amplitude"), Min >= -600.f);
	// It's hilly, not flat: the spread over about 136 m is a real fraction of the amplitude.
	TestTrue(TEXT("has relief"), Max - Min > 200.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainHeightNormalTest, "MuraBito.TerrainHeight.Normal", TerrainTestFlags)
bool FTerrainHeightNormalTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight H(3);
	for (const FVector2D& P : SamplePoints())
	{
		const FVector N = H.Normal(P.X, P.Y);
		TestTrue(TEXT("unit length"), FMath::IsNearlyEqual(N.Size(), 1.0, 1e-4));
		TestTrue(TEXT("points up"), N.Z > 0.0);
	}
	// A flat height function has a straight-up normal.
	const FTerrainHeight Flat(3, 0.f);
	TestTrue(TEXT("flat normal"), Flat.Normal(100.0, 200.0).Equals(FVector::UpVector, 1e-4));
	return true;
}

#endif
