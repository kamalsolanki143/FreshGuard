package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/kamalsolanki143/FreshGuard/plugin/cache"
	"github.com/kamalsolanki143/FreshGuard/plugin/hooks"
	"github.com/kamalsolanki143/FreshGuard/plugin/schemas"
)

var globalPlugin *hooks.FreshGuardPlugin

func init() {
	globalPlugin = hooks.NewPlugin(
		hooks.DefaultPluginConfig(),
		nil,
		cache.NewEvaluator(cache.NewDefaultPolicy(), cache.NewLedger(0)),
		nil,
	)
}

// GetName is the exported symbol required by Bifrost plugin loader.
func GetName() string {
	return globalPlugin.GetName()
}

// Init is the exported symbol required by Bifrost plugin loader.
func Init(config any) error {
	return globalPlugin.Init(config)
}

// PreLLMHook is the exported symbol called by Bifrost.
func PreLLMHook(ctx *schemas.BifrostContext, req *schemas.BifrostRequest) (*schemas.BifrostRequest, *schemas.LLMPluginShortCircuit, error) {
	return globalPlugin.PreLLMHook(ctx, req)
}

// PostLLMHook is the exported symbol called by Bifrost.
func PostLLMHook(ctx *schemas.BifrostContext, resp *schemas.BifrostResponse, e *schemas.BifrostError) (*schemas.BifrostResponse, *schemas.BifrostError, error) {
	return globalPlugin.PostLLMHook(ctx, resp, e)
}

func main() {
	verifyFlag := flag.Bool("verify", false, "Execute a test verification through FreshGuard plugin")
	textFlag := flag.String("text", "ChatGPT Plus costs $20 per month.", "LLM response text to verify")
	endpointFlag := flag.String("endpoint", "http://localhost:8000", "Verification service URL")
	apiKeyFlag := flag.String("api-key", "", "Optional X-API-Key")
	flag.Parse()

	if *verifyFlag {
		fmt.Printf("🛡️  FreshGuard CLI Verification Runner\n")
		fmt.Printf("Endpoint: %s\nText: %s\n\n", *endpointFlag, *textFlag)

		cfg := hooks.DefaultPluginConfig()
		cfg.VerificationServiceURL = *endpointFlag
		cfg.APIKey = *apiKeyFlag
		_ = globalPlugin.Init(cfg)

		bCtx := schemas.NewBifrostContext(context.Background(), "cli-demo-req")
		bReq := &schemas.BifrostRequest{
			ID:    "cli-demo-req",
			Model: "gpt-4o",
		}
		_, _, _ = globalPlugin.PreLLMHook(bCtx, bReq)

		providerResp := &schemas.BifrostResponse{
			ID:    "resp-cli-demo",
			Model: "gpt-4o",
			Choices: []schemas.BifrostChoice{
				{
					Message: schemas.ChatMessage{
						Role:    "assistant",
						Content: *textFlag,
					},
				},
			},
		}

		outResp, bifrostErr, err := globalPlugin.PostLLMHook(bCtx, providerResp, nil)
		if err != nil || bifrostErr != nil {
			fmt.Printf("❌ Hook Error: %v (BifrostErr: %v)\n", err, bifrostErr)
			os.Exit(1)
		}

		outJSON, _ := json.MarshalIndent(outResp.ExtraFields["freshguard"], "", "  ")
		fmt.Printf("✅ FreshGuard Output:\n%s\n", string(outJSON))
		os.Exit(0)
	}

	fmt.Printf("FreshGuard Bifrost Plugin (v1.0.0)\n")
	fmt.Printf("Plugin Name: %s\n", GetName())
	fmt.Printf("Default Policy TTLs:\n")
	policy := cache.NewDefaultPolicy()
	for cat, ttl := range policy.CategoryTTLs {
		fmt.Printf("  - %s: %v\n", cat, ttl)
	}
	os.Exit(0)
}
