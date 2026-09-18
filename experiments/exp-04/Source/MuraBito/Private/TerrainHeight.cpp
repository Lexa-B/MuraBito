#include "TerrainHeight.h"

FTerrainHeight::FTerrainHeight(int32 InSeed, float InAmplitude, float InWavelength, int32 InOctaves)
	: Seed(InSeed), Amplitude(InAmplitude), Wavelength(InWavelength)
{
	FRandomStream Stream(InSeed);
	for (int32 i = 0; i < FMath::Max(1, InOctaves); ++i)
	{
		OctaveOffsets.Add(FVector2D(Stream.FRandRange(-1000.f, 1000.f), Stream.FRandRange(-1000.f, 1000.f)));
	}
}

float FTerrainHeight::Height(double X, double Y) const
{
	double Sum = 0.0;
	double Norm = 0.0;
	double Frequency = 1.0 / Wavelength;
	double Weight = 1.0;
	for (const FVector2D& Offset : OctaveOffsets)
	{
		const FVector2D P = FVector2D(X, Y) * Frequency + Offset;
		Sum += Weight * FMath::PerlinNoise2D(P);
		Norm += Weight;
		Frequency *= 2.0;
		Weight *= 0.5;
	}
	const double Z = Amplitude * (Sum / Norm);
	return static_cast<float>(FMath::Clamp(Z, -static_cast<double>(Amplitude), static_cast<double>(Amplitude)));
}

FVector FTerrainHeight::Normal(double X, double Y) const
{
	constexpr double Eps = 10.0;
	const double DZDX = (Height(X + Eps, Y) - Height(X - Eps, Y)) / (2.0 * Eps);
	const double DZDY = (Height(X, Y + Eps) - Height(X, Y - Eps)) / (2.0 * Eps);
	return FVector(-DZDX, -DZDY, 1.0).GetSafeNormal();
}
