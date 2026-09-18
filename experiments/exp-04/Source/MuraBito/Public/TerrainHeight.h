#pragma once

#include "CoreMinimal.h"

/**
 * Seeded, deterministic terrain height: layered Perlin noise over XY, in cm.
 * The terrain mesh and the hex overlay both sample this, so the draped grid matches the surface exactly.
 */
struct MURABITO_API FTerrainHeight
{
	FTerrainHeight() : FTerrainHeight(0) {}
	explicit FTerrainHeight(int32 InSeed, float InAmplitude = 600.f, float InWavelength = 4000.f, int32 InOctaves = 4);

	/** Height at (X, Y). Always within [-Amplitude, Amplitude]. */
	float Height(double X, double Y) const;

	/** Unit surface normal at (X, Y), from central differences. */
	FVector Normal(double X, double Y) const;

	int32 GetSeed() const { return Seed; }
	float GetAmplitude() const { return Amplitude; }

private:
	int32 Seed;
	float Amplitude;
	float Wavelength;
	/** One random offset per octave, from Seed. Its length is the octave count. */
	TArray<FVector2D> OctaveOffsets;
};
